/* Copyright 2026 Ego Hygiene */
/* SPDX-License-Identifier: MIT */

(() => {
    "use strict";

    const body = document.body;
    const repository = body.dataset.riRepository;
    const route = body.dataset.riRoute;
    const commit = body.dataset.riCommit;
    if (!repository || !route || !commit) return;

    const knownRoutes = new Set([
        "now", "roadmap", "decisions", "journey", "dependencies", "health",
        "releases", "work", "search", "compare",
    ]);
    const storageKey = `egohygiene.repository-intelligence.resume.v1:${repository}`;
    const query = document.querySelector("[data-filter-query]");
    const state = document.querySelector("[data-filter-state]");
    const kind = document.querySelector("[data-filter-kind]");
    const reset = document.querySelector("[data-filter-reset]");
    const output = document.querySelector("[data-filter-results]");
    const empty = document.querySelector("[data-no-results]");
    const resume = document.querySelector("[data-resume-link]");
    const clearResume = document.querySelector("[data-clear-resume]");

    const readResume = () => {
        try {
            const value = JSON.parse(localStorage.getItem(storageKey) || "null");
            return value && knownRoutes.has(value.route) ? value : null;
        } catch {
            return null;
        }
    };

    const writeResume = () => {
        try {
            localStorage.setItem(storageKey, JSON.stringify({
                route,
                commit,
                q: query?.value.trim() || "",
                state: state?.value || "all",
                kind: kind?.value || "all",
                anchor: location.hash.startsWith("#") ? location.hash : "",
                recordedAt: new Date().toISOString(),
            }));
        } catch {
            // Storage can be unavailable by policy. The canonical page is unaffected.
        }
    };

    const resumeHref = (value) => {
        const root = new URL(document.querySelector(".ri-brand").href);
        const target = new URL(`${value.route}/`, root);
        if (value.q) target.searchParams.set("q", value.q);
        if (value.state && value.state !== "all") target.searchParams.set("state", value.state);
        if (value.kind && value.kind !== "all") target.searchParams.set("kind", value.kind);
        if (value.anchor) target.hash = value.anchor;
        return target.href;
    };

    const prior = readResume();
    if (resume && prior && (prior.route !== route || prior.commit !== commit || prior.anchor)) {
        resume.href = resumeHref(prior);
        resume.hidden = false;
        resume.textContent = prior.commit === commit ? "Resume last view" : "Resume prior snapshot position";
    }

    const params = new URLSearchParams(location.search);
    if (query) query.value = params.get("q") || "";
    if (state && [...state.options].some((option) => option.value === params.get("state"))) {
        state.value = params.get("state");
    }
    if (kind && [...kind.options].some((option) => option.value === params.get("kind"))) {
        kind.value = params.get("kind");
    }

    const apply = ({ updateUrl = true } = {}) => {
        const needle = query?.value.trim().toLocaleLowerCase() || "";
        const selectedState = state?.value || "all";
        const selectedKind = kind?.value || "all";
        let visible = 0;
        for (const item of document.querySelectorAll("[data-filter-item]")) {
            const matches =
                (!needle || (item.dataset.search || "").includes(needle)) &&
                (selectedState === "all" || item.dataset.state === selectedState) &&
                (selectedKind === "all" || item.dataset.kind === selectedKind);
            item.hidden = !matches;
            if (matches) visible += 1;
        }
        const filtering = Boolean(needle || selectedState !== "all" || selectedKind !== "all");
        if (output) output.value = filtering ? `${visible} matching records` : "Showing the full view";
        if (empty) empty.hidden = !filtering || visible > 0;
        if (updateUrl) {
            const next = new URL(location.href);
            const setOrDelete = (name, value, fallback = "") =>
                value && value !== fallback ? next.searchParams.set(name, value) : next.searchParams.delete(name);
            setOrDelete("q", needle);
            setOrDelete("state", selectedState, "all");
            setOrDelete("kind", selectedKind, "all");
            history.replaceState(null, "", `${next.pathname}${next.search}${next.hash}`);
        }
        writeResume();
    };

    query?.addEventListener("input", () => apply());
    state?.addEventListener("change", () => apply());
    kind?.addEventListener("change", () => apply());
    reset?.addEventListener("click", () => {
        if (query) query.value = "";
        if (state) state.value = "all";
        if (kind) kind.value = "all";
        apply();
        query?.focus();
    });
    clearResume?.addEventListener("click", () => {
        try { localStorage.removeItem(storageKey); } catch { /* no-op */ }
        if (resume) resume.hidden = true;
    });

    const navLinks = [...document.querySelectorAll(".ri-route-nav a")];
    for (const [index, link] of navLinks.entries()) {
        link.addEventListener("keydown", (event) => {
            let next = null;
            if (event.key === "ArrowDown" || event.key === "ArrowRight") next = (index + 1) % navLinks.length;
            if (event.key === "ArrowUp" || event.key === "ArrowLeft") next = (index - 1 + navLinks.length) % navLinks.length;
            if (event.key === "Home") next = 0;
            if (event.key === "End") next = navLinks.length - 1;
            if (next !== null) {
                event.preventDefault();
                navLinks[next].focus();
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        const editing = ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName);
        if (event.key === "/" && !editing && query) {
            event.preventDefault();
            query.focus();
        } else if (event.key === "Escape" && document.activeElement === query && query) {
            query.value = "";
            query.blur();
            apply();
        }
    });
    window.addEventListener("hashchange", writeResume);
    apply();
})();
