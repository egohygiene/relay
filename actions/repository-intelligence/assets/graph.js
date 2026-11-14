/* Copyright 2026 Ego Hygiene */
/* SPDX-License-Identifier: MIT */

(() => {
    "use strict";
    const contextKeys = new Set([
        "q", "state", "kind", "from", "to", "entity", "compare-left", "compare-right",
        "journey-left", "journey-right", "relationship", "assertion", "freshness", "scope",
        "check-state", "readiness", "implementation", "owner", "date", "domain", "component",
        "roadmap", "chapter", "release", "decision", "actor",
    ]);
    const width = 1200;
    const height = 600;

    for (const root of document.querySelectorAll("[data-ri-graph]")) {
        try {
            const svg = root.querySelector("[data-ri-graph-svg]");
            const controls = root.querySelector("[data-ri-graph-controls]");
            const select = root.querySelector("[data-ri-graph-select]");
            const neighbors = root.querySelector("[data-ri-graph-neighbors]");
            const inspector = root.querySelector("[data-ri-graph-inspector]");
            const heading = root.querySelector("[data-ri-graph-selected]");
            const detail = root.querySelector("[data-ri-graph-selected-detail]");
            const selectedLinks = root.querySelector("[data-ri-graph-selected-links]");
            const selectedEdges = root.querySelector("[data-ri-graph-selected-edges]");
            const status = root.querySelector("[data-ri-graph-status]");
            if (!svg || !controls || !select || !neighbors || !inspector || !heading || !detail || !selectedLinks || !selectedEdges || !status) continue;
            const base = new URL(root.dataset.riGraphRoot || "./", location.href);
            if (base.origin !== location.origin || !base.pathname.endsWith("/")) continue;
            const maximumY = Math.max(height, Math.min(50000, Number(root.dataset.riGraphHeight) || height));
            const directory = new Map([...root.querySelectorAll("[data-ri-graph-directory-node]")].map((node) => [node.dataset.riGraphDirectoryNode, node]));
            const nodes = new Map();
            for (const element of [...root.querySelectorAll("[data-ri-graph-node]")].slice(0, 112)) {
                const id = element.dataset.riGraphNode;
                const x = Number(element.dataset.riGraphX);
                const y = Number(element.dataset.riGraphY);
                if (!id || nodes.has(id) || !Number.isFinite(x) || !Number.isFinite(y) || !directory.has(id)) continue;
                nodes.set(id, { id, x, y, element, directory: directory.get(id), link: element.querySelector("a"),
                    label: element.dataset.riGraphLabel || "Untitled node", kind: element.dataset.riGraphKind || "unknown",
                    state: element.dataset.riGraphState || "unknown", repository: element.dataset.sourceRepository || "",
                    entity: element.dataset.entityId || "" });
            }
            const edgeDirectory = new Map([...root.querySelectorAll("[data-ri-graph-directory-edge]")].map((node) => [node.dataset.riGraphDirectoryEdge, node]));
            const edges = [...root.querySelectorAll("[data-ri-graph-edge]")].slice(0, 288).filter((edge) =>
                nodes.has(edge.dataset.riGraphSource) && nodes.has(edge.dataset.riGraphTarget));
            let camera = { x: width / 2, y: height / 2, zoom: 1 };
            let selected = "";
            let drag = null;

            const destination = (node) => {
                if (!node.link) return null;
                const raw = node.link.getAttribute("href");
                if (!raw || /[\\\u0000-\u0020\u007f]/u.test(raw)) return null;
                try {
                    const url = new URL(raw, location.href);
                    if (url.username || url.password) return null;
                    if (url.origin === base.origin && url.pathname.startsWith(base.pathname)) {
                        const path = url.pathname.slice(base.pathname.length);
                        if (!/^(?:[a-z0-9-]+\/)*$/u.test(path)) return null;
                        for (const [name] of url.searchParams) if (!contextKeys.has(name)) return null;
                        url.search = "";
                        for (const [name, value] of new URL(location.href).searchParams) {
                            if (contextKeys.has(name) && value.length <= 2048 && !url.searchParams.has(name)) url.searchParams.set(name, value);
                        }
                        if (node.entity) url.searchParams.set("entity", node.entity);
                        return url.href;
                    }
                    if (url.protocol !== "https:" || url.hostname !== "github.com" || url.port || url.search || /[%\\]/u.test(url.pathname)) return null;
                    if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/u.test(node.repository)) return null;
                    const prefix = `/${node.repository}`;
                    if (url.pathname !== prefix && !url.pathname.startsWith(`${prefix}/`)) return null;
                    if (url.pathname.split("/").some((part, index) => index > 0 && (!part || part === "." || part === ".."))) return null;
                    return url.href;
                } catch { return null; }
            };

            const connected = (id) => edges.filter((edge) => edge.dataset.riGraphSource === id || edge.dataset.riGraphTarget === id);
            const visible = () => {
                const ids = new Set([selected]);
                for (const edge of connected(selected)) { ids.add(edge.dataset.riGraphSource); ids.add(edge.dataset.riGraphTarget); }
                return !neighbors.checked || !selected ? [...nodes.values()] : [...nodes.values()].filter((node) => ids.has(node.id));
            };
            const draw = () => {
                camera = { x: Math.max(-width, Math.min(width * 2, camera.x)),
                    y: Math.max(-height, Math.min(maximumY + height, camera.y)), zoom: Math.max(0.02, Math.min(4, camera.zoom)) };
                const frameWidth = width / camera.zoom;
                const frameHeight = height / camera.zoom;
                svg.setAttribute("viewBox", `${camera.x - frameWidth / 2} ${camera.y - frameHeight / 2} ${frameWidth} ${frameHeight}`);
                const displayed = new Set(visible().map((node) => node.id));
                for (const node of nodes.values()) {
                    node.element.toggleAttribute("hidden", !displayed.has(node.id));
                    node.element.toggleAttribute("data-ri-graph-selected", node.id === selected);
                }
                let count = 0;
                for (const edge of edges) {
                    const present = displayed.has(edge.dataset.riGraphSource) && displayed.has(edge.dataset.riGraphTarget);
                    edge.toggleAttribute("hidden", !present);
                    edge.toggleAttribute("data-ri-graph-connected", edge.dataset.riGraphSource === selected || edge.dataset.riGraphTarget === selected);
                    if (present) count += 1;
                }
                status.textContent = `${displayed.size} admitted nodes and ${count} connections in this graph view. Zoom ${Math.round(camera.zoom * 100)}%.`;
            };
            const inspect = (id, updateUrl = true, center = true) => {
                const node = nodes.get(id);
                selected = node ? id : "";
                select.value = selected;
                neighbors.disabled = !node;
                inspector.hidden = !node;
                if (!node) neighbors.checked = false;
                selectedLinks.replaceChildren();
                selectedEdges.replaceChildren();
                if (node) {
                    heading.textContent = node.label;
                    detail.textContent = node.directory.querySelector("p")?.textContent || `${node.kind} · ${node.state}`;
                    const href = destination(node);
                    if (href) { const link = document.createElement("a"); link.href = href; link.textContent = "Open this view →"; selectedLinks.append(link); }
                    for (const edge of connected(id)) {
                        const item = document.createElement("li");
                        const entry = edgeDirectory.get(edge.dataset.riGraphEdge);
                        item.textContent = entry ? `${entry.querySelector("strong")?.textContent || ""}. ${entry.querySelector("p")?.textContent || ""}` : "Declared relationship details unavailable.";
                        selectedEdges.append(item);
                    }
                    if (!selectedEdges.children.length) { const item = document.createElement("li"); item.textContent = "No connections are projected; this does not prove independence."; selectedEdges.append(item); }
                    if (center) camera = { x: node.x, y: node.y, zoom: Math.max(0.85, camera.zoom) };
                }
                if (updateUrl) {
                    const next = new URL(location.href);
                    if (node) { next.searchParams.set("graph", id); if (node.entity) next.searchParams.set("entity", node.entity); }
                    else next.searchParams.delete("graph");
                    history.replaceState(null, "", `${next.pathname}${next.search}${next.hash}`);
                }
                draw();
            };
            const fit = () => {
                const entries = visible();
                if (!entries.length) return;
                const minimumX = Math.min(...entries.map((node) => node.x)) - 190;
                const maximumX = Math.max(...entries.map((node) => node.x)) + 190;
                const minimumY = Math.min(...entries.map((node) => node.y)) - 80;
                const maximum = Math.max(...entries.map((node) => node.y)) + 80;
                camera = { x: (minimumX + maximumX) / 2, y: (minimumY + maximum) / 2,
                    zoom: Math.min(1.4, width / (maximumX - minimumX), height / (maximum - minimumY)) };
                draw();
            };
            const action = (name) => {
                const stepX = width / camera.zoom * 0.2;
                const stepY = height / camera.zoom * 0.2;
                if (name === "in") camera.zoom *= 1.25;
                else if (name === "out") camera.zoom *= 0.8;
                else if (name === "left") camera.x -= stepX;
                else if (name === "right") camera.x += stepX;
                else if (name === "up") camera.y -= stepY;
                else if (name === "down") camera.y += stepY;
                else if (name === "reset") camera = { x: width / 2, y: height / 2, zoom: 1 };
                else if (name === "fit") return fit();
                draw();
            };
            select.addEventListener("change", () => inspect(select.value));
            neighbors.addEventListener("change", draw);
            for (const button of root.querySelectorAll("[data-ri-graph-action]")) button.addEventListener("click", () => action(button.dataset.riGraphAction));
            for (const button of root.querySelectorAll("[data-ri-graph-inspect]")) {
                button.hidden = false;
                button.addEventListener("click", () => inspect(button.dataset.riGraphInspect));
            }
            for (const node of nodes.values()) {
                if (!node.link) continue;
                for (const link of new Set([node.link, node.directory.querySelector("strong a")])) {
                    if (!link) continue;
                    const updateDestination = () => {
                        const href = destination(node);
                        if (href) link.setAttribute("href", href);
                    };
                    link.addEventListener("focus", () => { updateDestination(); inspect(node.id); });
                    link.addEventListener("pointerdown", updateDestination);
                    link.addEventListener("click", updateDestination);
                }
            }
            svg.setAttribute("tabindex", "0");
            svg.addEventListener("keydown", (event) => {
                if (event.target !== svg) return;
                const names = { ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down", "+": "in", "=": "in", "-": "out", Home: "reset", f: "fit", F: "fit" };
                if (names[event.key]) { event.preventDefault(); action(names[event.key]); }
            });
            svg.addEventListener("pointerdown", (event) => {
                if (event.button !== 0 || event.target.closest?.("[data-ri-graph-node]")) return;
                const matrix = svg.getScreenCTM();
                if (!matrix || !matrix.a || !matrix.d) return;
                svg.setPointerCapture(event.pointerId);
                drag = { id: event.pointerId, x: event.clientX, y: event.clientY, camera: { ...camera }, scaleX: 1 / matrix.a, scaleY: 1 / matrix.d };
            });
            svg.addEventListener("pointermove", (event) => {
                if (!drag || drag.id !== event.pointerId) return;
                camera = { ...drag.camera, x: drag.camera.x - (event.clientX - drag.x) * drag.scaleX,
                    y: drag.camera.y - (event.clientY - drag.y) * drag.scaleY };
                draw();
            });
            const endDrag = (event) => {
                if (!drag || drag.id !== event.pointerId) return;
                drag = null;
                if (svg.hasPointerCapture(event.pointerId)) svg.releasePointerCapture(event.pointerId);
            };
            svg.addEventListener("pointerup", endDrag);
            svg.addEventListener("pointercancel", endDrag);
            addEventListener("popstate", () => inspect(new URL(location.href).searchParams.get("graph") || "", false));
            root.classList.add("ri-graph--enhanced");
            controls.hidden = false;
            inspect(new URL(location.href).searchParams.get("graph") || "", false);
        } catch {
            // Static graph links and directories remain available after enhancement failure.
            const controls = root.querySelector("[data-ri-graph-controls]");
            if (controls) controls.hidden = true;
        }
    }
})();
