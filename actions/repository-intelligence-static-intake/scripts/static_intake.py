#!/usr/bin/env python3
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT
"""Offline, review-only admission of the website owner's Intelligence export.

Candidate bytes are data: no imports, installation, rendering, Git, network,
archive extraction or JavaScript execution occurs. Transport authenticity is a
separate caller obligation. Resource checks are a closed static markup profile,
not a proof about arbitrary JavaScript behavior or normalized model derivation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, UTC
import hashlib
from html.parser import HTMLParser
import importlib.util
import io
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import sys
from urllib.parse import unquote, urljoin, urlsplit
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
OWNER_LOCK = CONTRACTS / "export-owner.v1.lock.json"
MANIFEST_SCHEMA = CONTRACTS / "organization-intelligence-export.v1.schema.json"
ROUTES = CONTRACTS / "organization-routes.v1.json"
RECEIPT_SCHEMA = CONTRACTS / "static-intake-receipt.v1.schema.json"
ADMISSION_PATH = ROOT.parent / "repository-intelligence/scripts/public_catalog_admission.py"
MAX_FILE = 16 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_ARCHIVE = 80 * 1024 * 1024
MAX_MANIFEST = 256 * 1024
MAX_FILES = 256
MAX_ENTRIES = 512
HEX40 = re.compile(r"[a-f0-9]{40}")
HEX64 = re.compile(r"[a-f0-9]{64}")
ASSET = re.compile(r"assets/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+-[A-Za-z0-9_-]{8,}\.(?:js|css|svg|png|jpg|jpeg|gif|webp|avif|ico|woff|woff2|ttf|otf)")
TEXT_SUFFIXES = {".html", ".js", ".css", ".svg"}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self'; font-src 'self'; connect-src 'none'; object-src 'none'; "
       "frame-src 'none'; worker-src 'none'; base-uri 'none'; form-action 'none'")
DENIAL = "Static Intelligence export is incompatible with the review-only intake profile"


def require(condition):
    if not condition:
        raise ValueError(DENIAL)


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def pairs(entries):
    result = {}
    for key, value in entries:
        require(key not in result)
        result[key] = value
    return result


def text(content):
    result = content.decode("utf-8", errors="strict")
    require(not result.startswith("\ufeff") and "\x00" not in result
            and not any(0xD800 <= ord(character) <= 0xDFFF for character in result))
    return result


def document(content):
    return json.loads(text(content), object_pairs_hook=pairs,
                      parse_constant=lambda unused: require(False))


def instant(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value))
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _same(left, right):
    return encoded(left) == encoded(right)


def shape(value, schema):
    """Evaluate the bounded keyword subset used by the hash-bound owner schema.

    This is deliberately not a general JSON Schema implementation. Unknown
    assertion keywords fail closed when an owner compatibility resource changes.
    """
    descriptive = {"$schema", "$id", "title", "description", "$comment"}
    supported = {"type", "const", "enum", "properties", "required", "additionalProperties",
                 "items", "minItems", "maxItems", "uniqueItems", "minLength", "maxLength",
                 "pattern", "minimum", "maximum", "format", "allOf", "anyOf", "if", "then", "else"}
    require(isinstance(schema, dict) and not (set(schema) - descriptive - supported))
    if "type" in schema:
        kind = schema["type"]
        matches = {"object": type(value) is dict, "array": type(value) is list,
                   "string": type(value) is str, "integer": type(value) is int,
                   "null": value is None, "boolean": type(value) is bool}
        require(kind in matches and matches[kind])
    if "const" in schema:
        require(_same(value, schema["const"]))
    if "enum" in schema:
        require(any(_same(value, option) for option in schema["enum"]))
    for child in schema.get("allOf", []):
        shape(value, child)
    if "anyOf" in schema:
        valid = False
        for child in schema["anyOf"]:
            try:
                shape(value, child)
                valid = True
            except ValueError:
                pass
        require(valid)
    if "if" in schema:
        try:
            shape(value, schema["if"])
            branch = "then"
        except ValueError:
            branch = "else"
        if branch in schema:
            shape(value, schema[branch])
    if type(value) is dict:
        properties = schema.get("properties", {})
        require(set(schema.get("required", ())) <= set(value))
        if schema.get("additionalProperties") is False:
            require(set(value) <= set(properties))
        for key in set(value) & set(properties):
            shape(value[key], properties[key])
    if type(value) is list:
        require(schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", MAX_ENTRIES))
        if schema.get("uniqueItems"):
            require(len({encoded(item) for item in value}) == len(value))
        if "items" in schema:
            for item in value:
                shape(item, schema["items"])
    if type(value) is str:
        require(schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", MAX_TOTAL))
        require(not any(0xD800 <= ord(character) <= 0xDFFF for character in value))
        if "pattern" in schema:
            require(re.search(schema["pattern"], value) is not None)
        if "format" in schema:
            require(schema["format"] == "date-time")
            instant(value)
    if type(value) is int:
        require(schema.get("minimum", value) <= value <= schema.get("maximum", value))


def path_name(value, *, directory=False):
    require(isinstance(value, str) and 0 < len(value) <= 245 and value.isascii())
    if directory:
        require(value.endswith("/"))
        value = value[:-1]
    require(value and not value.startswith("/") and "\\" not in value
            and re.fullmatch(r"[A-Za-z0-9._/-]+", value) is not None)
    require(all(part not in {"", ".", "..", ".git"} for part in value.split("/")))
    return value


def local_path(value):
    result = Path(value).absolute()
    require(".." not in result.parts and ".git" not in result.parts
            and all(not part.is_symlink() for part in (result, *result.parents))
            and not any(ord(character) < 32 for character in str(result)))
    return result


def read_regular(path, limit, *, directory_fd=None):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    with os.fdopen(descriptor, "rb") as source:
        info = os.fstat(source.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size <= limit)
        content = source.read(limit + 1)
        require(len(content) == info.st_size and len(content) <= limit)
        return content


def parent_directories(files):
    return {str(parent) for name in files for parent in PurePosixPath(name).parents if str(parent) != "."}


def input_directory(source):
    require(source.is_dir())
    files, directories, total = {}, set(), 0
    for root, children, names, descriptor in os.fwalk(source, topdown=True, follow_symlinks=False):
        relative = Path(root).relative_to(source)
        require(len(files) + len(directories) + len(children) + len(names) <= MAX_ENTRIES)
        for name in children:
            value = (relative / name).as_posix()
            path_name(value)
            info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            require(stat.S_ISDIR(info.st_mode))
            directories.add(value)
        for name in names:
            value = (relative / name).as_posix()
            path_name(value)
            content = read_regular(name, MAX_MANIFEST if value == "export-manifest.json" else MAX_FILE,
                                   directory_fd=descriptor)
            total += len(content)
            require(total <= MAX_TOTAL + MAX_MANIFEST and len(files) < MAX_FILES + 1)
            files[value] = content
    return files, directories


def input_archive(source, expected):
    require(isinstance(expected, str) and HEX64.fullmatch(expected))
    content = read_regular(source, MAX_ARCHIVE)
    require(sha256(content) == expected)
    # Bound metadata before ZipFile allocates one ZipInfo per central entry.
    # Ordinary upload-artifact ZIPs need neither ZIP64 nor comments/multidisk.
    require(len(content) >= 22 and content[:4] == b"PK\x03\x04")
    signature, disk, central_disk, disk_entries, entry_count, central_size, central_offset, comment_size = struct.unpack("<4s4H2LH", content[-22:])
    require(signature == b"PK\x05\x06" and disk == central_disk == 0
            and disk_entries == entry_count and 0 < entry_count <= MAX_ENTRIES
            and central_size <= MAX_ENTRIES * 2048 and comment_size == 0
            and central_offset + central_size == len(content) - 22)
    files, directories, names, total = {}, set(), set(), 0
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = archive.infolist()
        require(len(entries) <= MAX_ENTRIES)
        for entry in entries:
            # orig_filename retains an embedded NUL that ZipInfo.filename truncates.
            require(entry.orig_filename == entry.filename)
            name = path_name(entry.filename, directory=entry.is_dir())
            require(name.casefold() not in names and not entry.flag_bits & 1
                    and entry.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED})
            names.add(name.casefold())
            mode = entry.external_attr >> 16
            kind = stat.S_IFMT(mode)
            require(kind in ({0, stat.S_IFDIR} if entry.is_dir() else {0, stat.S_IFREG}))
            if entry.is_dir():
                require(entry.file_size == 0)
                directories.add(name)
                continue
            limit = MAX_MANIFEST if name == "export-manifest.json" else MAX_FILE
            require(entry.file_size <= limit and entry.compress_size <= MAX_ARCHIVE
                    and entry.file_size <= max(1024 * 1024, entry.compress_size * 200))
            total += entry.file_size
            require(total <= MAX_TOTAL + MAX_MANIFEST and len(files) < MAX_FILES + 1)
            with archive.open(entry) as member:
                payload = member.read(limit + 1)
                require(len(payload) == entry.file_size and len(payload) <= limit)
            files[name] = payload
    return files, directories


def public_host(host):
    require(isinstance(host, str) and len(host) <= 253 and host == host.lower()
            and not host.endswith(".") and re.fullmatch(r"[a-z0-9.-]+", host))
    labels = host.split(".")
    require(len(labels) >= 2 and all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                                   for label in labels)
            and not labels[-1].isdigit()
            and not host.endswith((".local", ".localhost", ".internal", ".test", ".invalid", ".example")))
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return host
    require(False)


def origin(value):
    require(isinstance(value, str) and re.fullmatch(r"https://[a-z0-9.-]+", value))
    public_host(urlsplit(value).hostname)
    return value


def base_path(value):
    require(isinstance(value, str) and (value == "/.github/"
            or re.fullmatch(r"/(?:[a-z0-9][a-z0-9._-]*/)*", value)))
    require(all(part not in {".", ".."} for part in value.split("/") if part))
    return value


def clean_url(value):
    require(isinstance(value, str) and 0 < len(value) <= 4096 and "\\" not in value
            and not any(ord(character) <= 32 or ord(character) == 127 for character in value))
    require(not value.startswith("//"))
    parsed = urlsplit(value)
    require(not parsed.username and not parsed.password and parsed.port is None)
    require(re.search(r"%(?![a-fA-F0-9]{2})", parsed.path) is None)
    # Admit ordinary escaped public filenames, while rejecting encoded
    # separators, dot segments, controls and a second decoding boundary.
    for component in parsed.path.split("/"):
        decoded = unquote(component, errors="strict")
        require(decoded not in {".."} and not any(character in decoded for character in "/\\%")
                and not any(ord(character) < 32 or ord(character) == 127 for character in decoded)
                and not (decoded == "." and component != "."))
    return parsed


class Profile:
    def __init__(self, manifest, site, public_names):
        self.manifest = manifest
        self.site = site
        self.origin = manifest["target"]["origin"]
        self.base = manifest["target"]["base_path"]
        self.routes = {self.base.rstrip("/") + row["path"]: row for row in manifest["routes"]}
        self.public_names = public_names

    def resource(self, value, filename, suffixes=None):
        parsed = clean_url(value)
        require(not parsed.query and not parsed.fragment)
        resolved = urlsplit(urljoin(self.origin + self.base + filename, value))
        require(resolved.scheme == "https" and resolved.netloc == urlsplit(self.origin).netloc
                and resolved.path.startswith(self.base))
        name = resolved.path[len(self.base):]
        require(name in self.site and ASSET.fullmatch(name)
                and (suffixes is None or PurePosixPath(name).suffix in suffixes))
        return name

    def hyperlink(self, value, filename):
        parsed = clean_url(value)
        logical = next((row["path"] for row in self.manifest["routes"] if row["file"] == filename), "/")
        resolved = urlsplit(urljoin(self.origin + self.base.rstrip("/") + logical, value))
        if resolved.scheme == "https" and resolved.netloc == urlsplit(self.origin).netloc:
            if resolved.path in self.routes:
                return
        require(parsed.scheme == "https" and parsed.netloc == parsed.hostname and not parsed.query)
        host = public_host(parsed.hostname)
        components = [part for part in parsed.path.split("/") if part]
        if host == "github.com":
            require(len(components) >= 2 and "/".join(components[:2]) in self.public_names)
        elif host == "egohygiene.github.io":
            require(components and "egohygiene/" + components[0] in self.public_names)
        else:
            require(False)


def css(profile, value, filename):
    require("\x00" not in value)
    # Resolve CSS escapes before looking for resource syntax. This accepts a
    # deliberately bounded generated CSS dialect, not arbitrary authored CSS.
    value = re.sub(r"\\([0-9a-fA-F]{1,6})(?:\r\n|[ \t\r\n\f])?",
                   lambda match: chr(int(match.group(1), 16)) if 0 < int(match.group(1), 16) <= 0x10FFFF else "\x00", value)
    value = re.sub(r"\\([^\r\n\f])", r"\1", value)
    value = re.sub(r"/\*.*?\*/", "", value, flags=re.S)
    require("\x00" not in value and not re.search(r"@\s*import\b|(?:image-set|cross-fade|paint|expression)\s*\(", value, re.I))
    for match in re.finditer(r"url\s*\(([^()]*)\)", value, re.I):
        target = match.group(1).strip()
        if target[:1] in {"'", '"'}:
            require(len(target) > 1 and target[-1] == target[0])
            target = target[1:-1]
        if target.startswith("#"):
            require(re.fullmatch(r"#[A-Za-z0-9_:.-]+", target))
        else:
            profile.resource(target, filename, {".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".woff", ".woff2", ".ttf", ".otf"})
    require(len(re.findall(r"\burl\s*\(", value, re.I)) == len(re.findall(r"url\s*\([^()]*\)", value, re.I)))


class Markup(HTMLParser):
    """Closed HTML/SVG static profile for generated React output."""
    TAGS = set("html head title meta link body div main section article header footer nav aside h1 h2 h3 h4 h5 h6 p a ul ol li dl dt dd span strong em b i small code pre br hr button input label select option fieldset legend table thead tbody tfoot tr th td caption details summary progress time abbr bdi blockquote figure figcaption img picture source script noscript search svg g path circle ellipse rect line polyline polygon text tspan defs marker clippath lineargradient radialgradient stop use symbol mask title desc".split())
    VOID = {"meta", "link", "br", "hr", "input", "img", "source"}
    URI_ATTRS = {"src", "href", "xlink:href", "srcset", "poster", "background", "data", "action", "formaction", "ping", "srcdoc", "manifest", "codebase", "archive", "profile", "cite", "longdesc"}
    CSS_ATTRS = {"style", "fill", "stroke", "filter", "clip-path", "mask", "cursor", "marker", "marker-start", "marker-mid", "marker-end"}

    def __init__(self, profile, filename, route):
        super().__init__(convert_charrefs=True)
        self.profile, self.filename, self.route = profile, filename, route
        self.script = False
        self.csp = False
        self.canonical = 0
        self.refresh = 0
        self.stack = []
        self.head = False
        self.seen = set()
        self.doctype = False

    def handle_decl(self, declaration):
        require(declaration.lower() == "doctype html" and not self.doctype and not self.seen)
        self.doctype = True

    def unknown_decl(self, declaration):
        require(False)

    def handle_pi(self, data):
        require(False)

    def handle_starttag(self, tag, attributes):
        require(tag in self.TAGS and len(attributes) <= 64)
        parent = self.stack[-1] if self.stack else None
        if tag == "html":
            require(self.doctype and not self.seen and parent is None)
            self.seen.add(tag)
        elif tag == "head":
            require(parent == "html" and "head" not in self.seen and "body" not in self.seen)
            self.seen.add(tag)
        elif tag == "body":
            require(parent == "html" and "head" in self.seen and self.csp and "body" not in self.seen)
            self.seen.add(tag)
        else:
            require(parent is not None and parent != "html")
            if "body" not in self.seen:
                require("head" in self.stack and tag in {"title", "meta", "link", "script"}
                        and (parent == "head" or parent == "script"))
        if tag == "noscript":
            require("body" in self.stack and "noscript" not in self.stack and not attributes)
        if "noscript" in self.stack:
            require(tag == "p" and parent == "noscript"
                    and all(key == "class" for key, unused in attributes))
        require(len({key for key, unused in attributes}) == len(attributes))
        attrs = dict(attributes)
        require(all(not key.startswith("on") and key not in {"is", "autofocus", "form", "xmlns:xlink"}
                    and key != "xml:base"
                    and (value is None or len(value) <= 65536) for key, value in attributes))
        if tag == "head":
            require(not self.head)
            self.head = True
        if tag == "meta":
            require(parent == "head" and not (set(attrs) & self.URI_ATTRS))
            directive = attrs.get("http-equiv", "").lower()
            if directive == "content-security-policy":
                require(self.head and not self.csp and attrs.get("content") == CSP)
                self.csp = True
            elif directive == "refresh":
                require(self.csp and self.route is not None
                        and self.route["path"] != self.route["canonical_path"])
                target = self.profile.base.rstrip("/") + self.route["canonical_path"]
                require(attrs.get("content") in {prefix + destination
                        for prefix in ("0;url=", "0; url=")
                        for destination in (target, self.profile.origin + target)})
                self.refresh += 1
                require(self.refresh == 1)
            else:
                require(not directive)
        elif tag == "script":
            require(self.csp and not self.script and attrs.get("src")
                    and set(attrs) <= {"src", "type", "crossorigin", "defer"}
                    and attrs.get("type", "module") in {"module", "text/javascript"})
            self.profile.resource(attrs["src"], self.filename, {".js"})
            self.script = True
        elif tag == "link":
            require(self.csp and attrs.get("href") and not (set(attrs) & (self.URI_ATTRS - {"href"})))
            relation = attrs.get("rel", "").lower()
            if relation == "canonical":
                require(parent == "head" and self.route is not None)
                expected = self.profile.origin + self.profile.base.rstrip("/") + self.route["canonical_path"]
                require(attrs["href"] == expected)
                self.canonical += 1
            else:
                require(relation in {"stylesheet", "modulepreload", "preload", "icon"})
                suffixes = {".css"} if relation == "stylesheet" else {".js"} if relation == "modulepreload" else None
                self.profile.resource(attrs["href"], self.filename, suffixes)
        elif tag == "a":
            require(not (set(attrs) & (self.URI_ATTRS - {"href"})))
            if attrs.get("href"):
                self.profile.hyperlink(attrs["href"], self.filename)
        elif tag in {"img", "source"}:
            require(self.csp and not (set(attrs) & (self.URI_ATTRS - {"src", "srcset"})))
            if attrs.get("src"):
                self.profile.resource(attrs["src"], self.filename, {".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico"})
            if attrs.get("srcset"):
                for candidate in attrs["srcset"].split(","):
                    pieces = candidate.strip().split()
                    require(1 <= len(pieces) <= 2 and (len(pieces) == 1 or re.fullmatch(r"\d+(?:\.\d+)?[wx]", pieces[1])))
                    self.profile.resource(pieces[0], self.filename)
        elif tag == "use":
            require(not (set(attrs) & (self.URI_ATTRS - {"href", "xlink:href"})))
            for key in {"href", "xlink:href"} & set(attrs):
                require(isinstance(attrs[key], str) and re.fullmatch(r"#[A-Za-z0-9_:.-]+", attrs[key]))
        else:
            require(not (set(attrs) & self.URI_ATTRS))
        for key, value in attributes:
            if key in self.CSS_ATTRS:
                css(self.profile, value or "", self.filename)
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attributes):
        require(tag != "script")
        self.handle_starttag(tag, attributes)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        require(tag in self.TAGS and tag not in self.VOID and self.stack and self.stack[-1] == tag)
        self.stack.pop()
        if tag == "script":
            require(self.script)
            self.script = False
        elif tag == "head":
            require(self.csp)
            self.head = False

    def handle_data(self, data):
        require(not self.script or not data.strip())
        if not self.stack or self.stack[-1] in {"html", "head"}:
            require(not data.strip())

    def finish(self):
        self.close()
        require(self.csp and not self.script and not self.head and not self.stack
                and self.seen == {"html", "head", "body"}
                and self.canonical == (1 if self.route is not None else 0))
        if self.route is not None and self.route["path"] != self.route["canonical_path"]:
            require(self.refresh == 1)


def javascript(profile, value, filename):
    """Diagnose recognizable literal module edges without qualifying JavaScript.

    Lexical uncertainty ends this optional diagnostic; it does not qualify
    arbitrary JavaScript or certify absent module edges. The independently
    enforced HTML/CSP resource profile remains mandatory. Browser/module and
    application qualification is explicitly unavailable in the receipt.
    """
    # Tokenize ordinary generated ESM strings/comments rather than relying on
    # whitespace (minified import{a}from"./chunk.js" is normal output). This is
    # not a JavaScript parser: computed behavior and template expressions remain
    # outside the recorded execution-qualification boundary.
    tokens = []
    cursor = 0
    while cursor < len(value):
        if len(tokens) >= 500000:
            break
        character = value[cursor]
        if character.isspace():
            cursor += 1
        elif value.startswith("//", cursor):
            end = value.find("\n", cursor + 2)
            cursor = len(value) if end < 0 else end + 1
        elif value.startswith("/*", cursor):
            end = value.find("*/", cursor + 2)
            if end < 0:
                break
            cursor = end + 2
        elif character == "/" and (not tokens or tokens[-1][1] in {
                "=", "(", "[", "{", ",", ":", ";", "!", "?", "&", "|", "+", "-", "*", "%", "^", "~", "<", ">",
                "return", "throw", "case", "delete", "void", "typeof", "in", "of", "yield", "await"}):
            # Regex literals have their own quote/escape/character-class
            # syntax. Do not mistake React's /["'&<>]/ for an unterminated
            # JavaScript string. This bounded generated dialect is not an
            # arbitrary-language JavaScript validator.
            start, inside_class, end = cursor, False, cursor + 1
            while end < len(value) and value[end] not in "\r\n":
                if value[end] == "\\":
                    end += 2
                    continue
                if value[end] == "[":
                    inside_class = True
                elif value[end] == "]":
                    inside_class = False
                elif value[end] == "/" and not inside_class:
                    break
                end += 1
            if end >= len(value) or value[end] in "\r\n":
                # Postfix division can look like a regex start without a full
                # parser (count++/2). Keep it punctuation, never certify syntax.
                tokens.append(("punctuation", character))
                cursor = start + 1
                continue
            cursor = end
            cursor += 1
            while cursor < len(value) and value[cursor].isalpha():
                cursor += 1
            tokens.append(("regex", value[start:cursor]))
        elif character in {"'", '"', "`"}:
            quote, start = character, cursor + 1
            cursor += 1
            while cursor < len(value) and value[cursor] != quote:
                cursor += 2 if value[cursor] == "\\" else 1
            if cursor >= len(value):
                break
            tokens.append(("template" if quote == "`" else "string", value[start:cursor]))
            cursor += 1
        elif character.isalpha() or character in "_$":
            start = cursor
            cursor += 1
            while cursor < len(value) and (value[cursor].isalnum() or value[cursor] in "_$"):
                cursor += 1
            tokens.append(("word", value[start:cursor]))
        else:
            tokens.append(("punctuation", character))
            cursor += 1
    for index, token in enumerate(tokens):
        if token not in {("word", "import"), ("word", "export")} or (index and tokens[index - 1][1] == "."):
            continue
        following = tokens[index + 1:index + 3]
        specifier = None
        if token[1] == "import" and following and following[0][0] == "string":
            specifier = following[0][1]
        elif token[1] == "import" and len(following) == 2 and following[0][1] == "(" and following[1][0] == "string":
            specifier = following[1][1]
        elif following and following[0][1] not in {"(", "."}:
            # Static import/export declarations cannot cross a statement's
            # semicolon. Generated declarations use the literal `from` token.
            for offset in range(index + 1, min(len(tokens) - 1, index + 512)):
                if tokens[offset][1] == ";":
                    break
                if tokens[offset] == ("word", "from") and tokens[offset + 1][0] == "string":
                    specifier = tokens[offset + 1][1]
                    break
        if specifier is not None:
            require("\\" not in specifier)
            profile.resource(specifier, filename, {".js"})
    # These are transport conveniences, never an executable acceptance signal.
    require(not re.search(r"(?m)^\s*//#\s*sourceMappingURL=", value))


def svg(profile, value, filename):
    require(not re.search(r"<!DOCTYPE|<!ENTITY", value, re.I))
    root = ET.fromstring(value)
    require(root.tag == "{http://www.w3.org/2000/svg}svg")
    for element in root.iter():
        require(element.tag.startswith("{http://www.w3.org/2000/svg}"))
        tag = element.tag.rsplit("}", 1)[-1].lower()
        require(tag in Markup.TAGS - {"script", "html", "body", "head", "input", "button", "a"})
        for attribute, content in element.attrib.items():
            key = attribute.rsplit("}", 1)[-1].lower()
            require(not key.startswith("on") and attribute != "{http://www.w3.org/XML/1998/namespace}base")
            if key in {"href", "src"}:
                require(re.fullmatch(r"#[A-Za-z0-9_:.-]+", content))
            if key in Markup.CSS_ATTRS:
                css(profile, content, filename)


def owner_resources():
    lock = document(OWNER_LOCK.read_bytes())
    require(type(lock) is dict and set(lock) == {"schema", "owner", "revision", "files"}
            and lock["schema"] == "egohygiene.relay.organization-intelligence-export-owner/v1"
            and lock["owner"] == "egohygiene/egohygiene.io" and HEX40.fullmatch(lock["revision"]))
    expected = {
        "contracts/organization-intelligence/export/export-manifest.v1.schema.json": MANIFEST_SCHEMA,
        "contracts/organization-intelligence/export/organization-routes.v1.json": ROUTES,
    }
    require(type(lock["files"]) is dict and set(lock["files"]) == set(expected))
    for source, mirror in expected.items():
        require(HEX64.fullmatch(lock["files"][source]) and sha256(mirror.read_bytes()) == lock["files"][source])
    return lock, document(MANIFEST_SCHEMA.read_bytes()), document(ROUTES.read_bytes())["routes"]


def admission_module():
    specification = importlib.util.spec_from_file_location("relay_static_export_public_catalog", ADMISSION_PATH)
    require(specification is not None and specification.loader is not None)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def validate(files, directories, *, manifest_sha256, producer_commit, target_origin, target_base):
    require(isinstance(manifest_sha256, str) and HEX64.fullmatch(manifest_sha256)
            and isinstance(producer_commit, str) and HEX40.fullmatch(producer_commit))
    origin(target_origin)
    base_path(target_base)
    require("export-manifest.json" in files and len(files["export-manifest.json"]) <= MAX_MANIFEST)
    manifest_bytes = files["export-manifest.json"]
    manifest = document(manifest_bytes)
    # Public selection is authenticated before reporting payload identities,
    # counts or digests. A manifest's own public flag is insufficient.
    require(type(manifest) is dict and manifest.get("visibility") == "public")
    scope = manifest.get("scope")
    require(type(scope) is dict and scope.get("kind") == "organization")
    admission = admission_module()
    admission.validate_identities(scope.get("repositories"), scope.get("admission"))
    lock, schema, routes = owner_resources()
    shape(manifest, schema)
    require(sha256(manifest_bytes) == manifest_sha256
            and manifest["producer"]["revision"] == producer_commit
            and manifest["target"] == {"origin": target_origin, "base_path": target_base}
            and _same(manifest["routes"], routes))
    instant(manifest["as_of"])
    inventory = manifest["files"]
    require(inventory == sorted(inventory, key=lambda row: row["path"]))
    names = [path_name(row["path"]) for row in inventory]
    require(len(names) == len(set(name.casefold() for name in names)))
    route_files = {row["file"] for row in routes}
    required = route_files | {"404.html", ".nojekyll"}
    require(required <= set(names) and all(name in required or ASSET.fullmatch(name) for name in names))
    require(set(files) == {"export-manifest.json"} | {"site/" + name for name in names})
    require(directories <= parent_directories(files)
            and not (set(files) & parent_directories(files))
            and len({name.casefold() for name in set(files) | directories}) == len(set(files) | directories))
    site = {name: files["site/" + name] for name in names}
    require(site[".nojekyll"] == b"" and sum(len(content) for content in site.values()) <= MAX_TOTAL)
    for row in inventory:
        content = site[row["path"]]
        require(len(content) == row["size_bytes"] and sha256(content) == row["sha256"])
    public_names = {row["full_name"] for row in admission.public_document()["repositories"]
                    if row["visibility"] == "public"}
    profile = Profile(manifest, site, public_names)
    by_file = {row["file"]: row for row in routes}
    for name, content in site.items():
        suffix = PurePosixPath(name).suffix
        if suffix in TEXT_SUFFIXES:
            value = text(content)
            if suffix == ".html":
                parser = Markup(profile, name, by_file.get(name))
                parser.feed(value)
                parser.finish()
            elif suffix == ".css":
                css(profile, value, name)
            elif suffix == ".js":
                javascript(profile, value, name)
            else:
                svg(profile, value, name)
    return manifest, lock


def receipt(manifest, lock, *, manifest_sha256, archive_sha256):
    return {
        "schema": "egohygiene.relay.organization-intelligence-static-intake/v1",
        "contract_version": "1.0.0-alpha.1", "publication": "review-only",
        "deployment_authorized": False,
        "producer": manifest["producer"], "target": manifest["target"], "as_of": manifest["as_of"],
        "scope": manifest["scope"], "models": manifest["models"],
        "input": {"transport": "zip" if archive_sha256 is not None else "directory",
                  "archive_sha256": archive_sha256, "manifest_sha256": manifest_sha256},
        "inventory": {"files_sha256": sha256(encoded(manifest["files"])),
                      "file_count": len(manifest["files"]),
                      "size_bytes": sum(row["size_bytes"] for row in manifest["files"])},
        "validation": {"profile": "intelligence-static-markup/v1", "public_scope": "authenticated",
                       "manifest_and_inventory": "verified", "model_derivation": "producer-declared-not-replayed",
                       "literal_module_edges": "diagnostic-only",
                       "script_execution": "not-performed", "browser_qualification": "unavailable",
                       "hosting_transition": "not-admitted"},
        "implementation": {"sha256": sha256(Path(__file__).read_bytes()),
                           "receipt_schema_sha256": sha256(RECEIPT_SCHEMA.read_bytes()),
                           "public_admission_sha256": sha256(ADMISSION_PATH.read_bytes()),
                           "owner_lock_sha256": sha256(OWNER_LOCK.read_bytes()),
                           "owner": lock},
    }


def stage(output, files, evidence):
    require(not output.exists() and not output.is_symlink() and output.parent.is_dir())
    # Exclusively create after every candidate byte has passed validation. No
    # metadata or executable modes from the candidate are preserved.
    output.mkdir(mode=0o700)
    try:
        for name, content in sorted(files.items()):
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with target.open("xb") as handle:
                handle.write(content)
            target.chmod(0o600)
        evidence_bytes = encoded(evidence)
        with (output / "intake-receipt.json").open("xb") as handle:
            handle.write(evidence_bytes)
        (output / "intake-receipt.json").chmod(0o600)
    except BaseException:
        shutil.rmtree(output)
        raise
    return {"review-directory": str(output), "site-directory": str(output / "site"),
            "receipt-path": str(output / "intake-receipt.json"),
            "receipt-sha256": sha256(evidence_bytes), "publication": "review-only"}


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(DENIAL)


def main():
    parser = Arguments(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--archive")
    inputs.add_argument("--directory")
    parser.add_argument("--archive-sha256")
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--producer-commit", required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--base-path", required=True)
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--github-output")
    try:
        args = parser.parse_args()
        source = local_path(args.archive or args.directory)
        output = local_path(args.output_directory)
        require(output != source and source not in output.parents and output not in source.parents)
        if args.archive:
            files, directories = input_archive(source, args.archive_sha256)
        else:
            require(args.archive_sha256 is None)
            files, directories = input_directory(source)
        manifest, lock = validate(files, directories, manifest_sha256=args.manifest_sha256,
            producer_commit=args.producer_commit, target_origin=args.origin, target_base=args.base_path)
        evidence = receipt(manifest, lock, manifest_sha256=args.manifest_sha256,
                           archive_sha256=args.archive_sha256)
        shape(evidence, document(RECEIPT_SCHEMA.read_bytes()))
        outputs = stage(output, files, evidence)
        if args.github_output:
            # The caller supplies this runner-created file; no candidate field
            # can introduce a workflow-command line or select its destination.
            destination = local_path(args.github_output)
            with destination.open("a", encoding="utf-8") as handle:
                for key, value in outputs.items():
                    handle.write(key + "=" + value + "\n")
        print(json.dumps(outputs, sort_keys=True))
        return 0
    except Exception:
        # No raw payload, path, protected identity, parser error or traceback is
        # reflected into a public Actions log on a denied capture.
        print(DENIAL, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
