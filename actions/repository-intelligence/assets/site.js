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
                scrollY: Math.max(0, Math.round(window.scrollY)),
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
        if (value.commit === commit && Number(value.scrollY) > 0) target.searchParams.set("resume", "1");
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

    const includesToken = (item, singular, plural, expected) => {
        if (expected === "all") return true;
        const tokens = (item.dataset[plural] || item.dataset[singular] || "")
            .split(/\s+/u)
            .filter(Boolean);
        return tokens.includes(expected);
    };

    const setOrDelete = (url, name, value, fallback = "") => {
        if (value && value !== fallback) url.searchParams.set(name, value);
        else url.searchParams.delete(name);
    };

    const evidenceWindows = [];

    const setupEvidenceWindow = (viewport) => {
        const list = viewport.querySelector(".ri-evidence-list");
        if (!list) return;
        const items = [...list.querySelectorAll("[data-evidence-item]")];
        const threshold = 48;
        if (items.length <= threshold) return;
        const rowHeight = Math.max(1, Number(viewport.dataset.rowHeight) || 150);
        const overscan = 4;
        let frame = null;
        viewport.dataset.virtualized = "true";

        const spacer = (height) => {
            const item = document.createElement("li");
            item.className = "ri-virtual-space";
            item.style.setProperty("--ri-virtual-space", `${height}px`);
            item.setAttribute("aria-hidden", "true");
            return item;
        };

        const render = () => {
            const viewportHeight = viewport.clientHeight || 496;
            const visibleStart = Math.floor(viewport.scrollTop / rowHeight);
            const visibleCount = Math.ceil(viewportHeight / rowHeight);
            const start = Math.max(0, visibleStart - overscan);
            const end = Math.min(items.length, visibleStart + visibleCount + overscan);
            const fragment = document.createDocumentFragment();
            if (start > 0) fragment.append(spacer(start * rowHeight));
            for (let index = start; index < end; index += 1) {
                const item = items[index];
                item.setAttribute("aria-posinset", String(index + 1));
                item.setAttribute("aria-setsize", String(items.length));
                fragment.append(item);
            }
            if (end < items.length) fragment.append(spacer((items.length - end) * rowHeight));
            list.replaceChildren(fragment);
        };

        const schedule = () => {
            if (frame !== null) cancelAnimationFrame(frame);
            frame = requestAnimationFrame(() => {
                render();
                frame = null;
            });
        };
        viewport.addEventListener("scroll", schedule, { passive: true });
        evidenceWindows.push({ viewport, render });
        render();
    };

    for (const viewport of document.querySelectorAll("[data-evidence-viewport]")) {
        setupEvidenceWindow(viewport);
    }

    const apply = ({ updateUrl = true } = {}) => {
        const needle = query?.value.trim().toLocaleLowerCase() || "";
        const selectedState = state?.value || "all";
        const selectedKind = kind?.value || "all";
        let visible = 0;
        for (const item of document.querySelectorAll("[data-filter-item]")) {
            const matches =
                (!needle || (item.dataset.search || "").includes(needle)) &&
                includesToken(item, "state", "states", selectedState) &&
                includesToken(item, "kind", "kinds", selectedKind);
            item.hidden = !matches;
            if (matches) visible += 1;
        }
        for (const chapter of document.querySelectorAll(".ri-roadmap-chapter")) {
            chapter.hidden = !chapter.querySelector("[data-roadmap-quest]:not([hidden])");
        }
        for (const mapLink of document.querySelectorAll("[data-minimap-quest]")) {
            const target = document.getElementById(mapLink.hash.slice(1));
            mapLink.closest("li").hidden = Boolean(target?.hidden);
        }
        const filtering = Boolean(needle || selectedState !== "all" || selectedKind !== "all");
        if (output) output.value = filtering ? `${visible} matching records` : "Showing the full view";
        if (empty) empty.hidden = !filtering || visible > 0;
        if (updateUrl) {
            const next = new URL(location.href);
            setOrDelete(next, "q", needle);
            setOrDelete(next, "state", selectedState, "all");
            setOrDelete(next, "kind", selectedKind, "all");
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

    const questLinks = [...document.querySelectorAll("[data-quest-link]")];
    for (const [index, link] of questLinks.entries()) {
        link.addEventListener("keydown", (event) => {
            let next = null;
            if (event.key === "ArrowDown" || event.key === "ArrowRight") next = Math.min(index + 1, questLinks.length - 1);
            if (event.key === "ArrowUp" || event.key === "ArrowLeft") next = Math.max(index - 1, 0);
            if (event.key === "Home") next = 0;
            if (event.key === "End") next = questLinks.length - 1;
            if (next !== null) {
                event.preventDefault();
                questLinks[next].focus();
            }
        });
    }

    const minimapLinks = [...document.querySelectorAll("[data-minimap-quest]")];
    const markSelectedQuest = (identifier) => {
        for (const quest of document.querySelectorAll("[data-roadmap-quest]")) {
            quest.toggleAttribute("data-selected", quest.id === identifier);
        }
        for (const link of minimapLinks) {
            if (link.hash.slice(1) === identifier) link.setAttribute("aria-current", "step");
            else link.removeAttribute("aria-current");
        }
    };

    const applyHashSelection = () => {
        const identifier = location.hash.slice(1);
        const selected = document.getElementById(identifier);
        if (!selected?.matches("[data-roadmap-quest]")) return;
        markSelectedQuest(identifier);
        const evidence = selected.querySelector("[data-quest-evidence]");
        if (evidence) evidence.open = true;
        writeResume();
    };

    for (const details of document.querySelectorAll("[data-quest-evidence]")) {
        details.addEventListener("toggle", () => {
            if (!details.open) return;
            const quest = details.closest("[data-roadmap-quest]");
            if (!quest) return;
            const next = new URL(location.href);
            next.hash = quest.id;
            history.replaceState(null, "", `${next.pathname}${next.search}${next.hash}`);
            markSelectedQuest(quest.id);
            const viewport = details.querySelector("[data-evidence-viewport]");
            evidenceWindows.find((entry) => entry.viewport === viewport)?.render();
            writeResume();
        });
    }

    if ("IntersectionObserver" in window && minimapLinks.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            const current = entries
                .filter((entry) => entry.isIntersecting && !entry.target.hidden)
                .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
            if (current && !location.hash) markSelectedQuest(current.target.id);
        }, { rootMargin: "-18% 0px -68%", threshold: [0.05, 0.25, 0.6] });
        for (const quest of document.querySelectorAll("[data-roadmap-quest]")) observer.observe(quest);
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

    let scrollFrame = null;
    window.addEventListener("scroll", () => {
        if (scrollFrame !== null) return;
        scrollFrame = requestAnimationFrame(() => {
            writeResume();
            scrollFrame = null;
        });
    }, { passive: true });
    window.addEventListener("hashchange", applyHashSelection);
    apply({ updateUrl: false });
    applyHashSelection();
    if (params.get("resume") === "1" && prior?.route === route && prior.commit === commit) {
        requestAnimationFrame(() => {
            if (!location.hash && Number(prior.scrollY) > 0) {
                window.scrollTo({ top: Number(prior.scrollY), behavior: "auto" });
            }
            const resumed = new URL(location.href);
            resumed.searchParams.delete("resume");
            history.replaceState(null, "", `${resumed.pathname}${resumed.search}${resumed.hash}`);
        });
    }
})();
