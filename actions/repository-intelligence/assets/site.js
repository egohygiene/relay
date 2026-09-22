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
        "intelligence", "now", "roadmap", "decisions", "journey", "dependencies", "health",
        "releases", "work", "search", "compare",
    ]);
    const transferableContext = new Set([
        "q", "state", "kind", "from", "to", "entity",
        "compare-left", "compare-right", "journey-left", "journey-right",
        "relationship", "assertion", "freshness", "scope", "check-state", "readiness",
        "implementation", "owner", "date", "domain", "component", "roadmap", "chapter",
        "release", "decision", "actor",
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
    const extraFilters = [...document.querySelectorAll("[data-filter-extra]")];
    const journeyDateFrom = document.querySelector("[data-journey-date-from]");
    const journeyDateTo = document.querySelector("[data-journey-date-to]");

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
                filters: Object.fromEntries(extraFilters.map((filter) => [
                    filter.dataset.filterExtra,
                    filter.value || "all",
                ])),
                dateFrom: journeyDateFrom?.value || "",
                dateTo: journeyDateTo?.value || "",
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
        const target = value.route === "intelligence"
            ? new URL("./", root)
            : new URL(`${value.route}/`, root);
        if (value.q) target.searchParams.set("q", value.q);
        if (value.state && value.state !== "all") target.searchParams.set("state", value.state);
        if (value.kind && value.kind !== "all") target.searchParams.set("kind", value.kind);
        for (const [name, selected] of Object.entries(value.filters || {})) {
            if (selected && selected !== "all") target.searchParams.set(name, selected);
        }
        if (value.dateFrom) target.searchParams.set("from", value.dateFrom);
        if (value.dateTo) target.searchParams.set("to", value.dateTo);
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
    for (const filter of extraFilters) {
        const selected = params.get(filter.dataset.filterExtra);
        if ([...filter.options].some((option) => option.value === selected)) {
            filter.value = selected;
        }
    }
    if (journeyDateFrom) journeyDateFrom.value = params.get("from") || "";
    if (journeyDateTo) journeyDateTo.value = params.get("to") || "";

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

    const contextLinks = [
        ...document.querySelectorAll("[data-preserve-context-links] a, [data-preserve-context]"),
    ];
    const contextTargets = new WeakMap(
        contextLinks.map((link) => [link, link.getAttribute("href")]),
    );
    let selectedEntity = params.get("entity") || "";
    let selectedEntityNode = null;
    const entityNodes = [...document.querySelectorAll("[data-entity-id]")];
    const entityFromHash = () => {
        const selected = document.getElementById(location.hash.slice(1));
        return selected?.closest("[data-entity-id]")?.dataset.entityId || "";
    };
    const preserveContext = (link) => {
        const original = contextTargets.get(link);
        if (!original) return;
        const target = new URL(original, location.href);
        const current = new URL(location.href);
        if (target.origin !== current.origin) {
            link.href = target.href;
            return;
        }
        for (const [name, value] of current.searchParams) {
            if (transferableContext.has(name) && !target.searchParams.has(name)) {
                target.searchParams.append(name, value);
            }
        }
        const entity = entityFromHash() || selectedEntity;
        if (entity && !target.searchParams.has("entity")) {
            target.searchParams.set("entity", entity);
        }
        link.href = target.href;
    };
    const refreshContextLinks = () => {
        for (const link of contextLinks) preserveContext(link);
    };
    const selectContextEntity = (node, { updateUrl = true, reveal = false } = {}) => {
        const identifier = node?.dataset.entityId;
        if (!identifier) return;
        selectedEntity = identifier;
        body.dataset.contextEntity = identifier;
        selectedEntityNode?.removeAttribute("data-context-selected");
        node.setAttribute("data-context-selected", "");
        selectedEntityNode = node;
        if (updateUrl) {
            const next = new URL(location.href);
            next.searchParams.set("entity", identifier);
            history.replaceState(null, "", `${next.pathname}${next.search}${next.hash}`);
        }
        refreshContextLinks();
        if (reveal) {
            let disclosure = node.closest("details");
            while (disclosure) {
                disclosure.open = true;
                disclosure = disclosure.parentElement?.closest("details") || null;
            }
            requestAnimationFrame(() => node.scrollIntoView({ block: "center" }));
        }
    };
    for (const link of contextLinks) {
        preserveContext(link);
        link.addEventListener("focus", () => preserveContext(link));
        link.addEventListener("pointerdown", () => preserveContext(link));
        link.addEventListener("click", () => preserveContext(link));
    }
    const selectEventEntity = (event) => {
        const node = event.target.closest?.("[data-entity-id]");
        if (node) selectContextEntity(node);
    };
    document.addEventListener("focusin", selectEventEntity);
    document.addEventListener("pointerdown", selectEventEntity);
    if (selectedEntity) {
        const requested = entityNodes.find((node) => node.dataset.entityId === selectedEntity);
        if (requested) selectContextEntity(requested, { updateUrl: false, reveal: !location.hash });
    }

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
        const selectedExtras = Object.fromEntries(extraFilters.map((filter) => [
            filter.dataset.filterExtra,
            filter.value || "all",
        ]));
        const selectedFrom = journeyDateFrom?.value || "";
        const selectedTo = journeyDateTo?.value || "";
        let visible = 0;
        for (const item of document.querySelectorAll("[data-filter-item]")) {
            const matchesExtras = Object.entries(selectedExtras).every(([name, expected]) => {
                if (expected === "all") return true;
                return (item.getAttribute(`data-filter-${name}`) || "")
                    .split(/\s+/u)
                    .filter(Boolean)
                    .includes(expected);
            });
            const occurredDate = (item.dataset.journeyOccurredAt || "").slice(0, 10);
            const matchesDate = !occurredDate || (
                (!selectedFrom || occurredDate >= selectedFrom) &&
                (!selectedTo || occurredDate <= selectedTo)
            );
            const matches =
                (!needle || (item.dataset.search || "").includes(needle)) &&
                includesToken(item, "state", "states", selectedState) &&
                includesToken(item, "kind", "kinds", selectedKind) &&
                matchesExtras && matchesDate;
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
        for (const group of document.querySelectorAll("[data-decision-group]")) {
            group.hidden = !group.querySelector("[data-decision-record]:not([hidden])");
        }
        for (const mapLink of document.querySelectorAll("[data-decision-index]")) {
            const target = document.getElementById(mapLink.hash.slice(1));
            mapLink.closest("li").hidden = Boolean(target?.hidden);
        }
        for (const group of document.querySelectorAll("[data-decision-index-group]")) {
            group.hidden = !group.querySelector("[data-decision-index]:not([hidden])");
        }
        for (const chapter of document.querySelectorAll("[data-journey-chapter]")) {
            chapter.hidden = !chapter.querySelector("[data-journey-event]:not([hidden])");
        }
        for (const mapLink of document.querySelectorAll("[data-journey-index]")) {
            const target = document.getElementById(mapLink.hash.slice(1));
            mapLink.closest("li").hidden = Boolean(target?.hidden);
        }
        const filtering = Boolean(
            needle || selectedState !== "all" || selectedKind !== "all" ||
            selectedFrom || selectedTo ||
            Object.values(selectedExtras).some((value) => value !== "all")
        );
        if (output) output.value = filtering ? `${visible} matching records` : "Showing the full view";
        if (empty) empty.hidden = !filtering || visible > 0;
        if (updateUrl) {
            const next = new URL(location.href);
            setOrDelete(next, "q", needle);
            setOrDelete(next, "state", selectedState, "all");
            setOrDelete(next, "kind", selectedKind, "all");
            for (const [name, selected] of Object.entries(selectedExtras)) {
                setOrDelete(next, name, selected, "all");
            }
            setOrDelete(next, "from", selectedFrom);
            setOrDelete(next, "to", selectedTo);
            history.replaceState(null, "", `${next.pathname}${next.search}${next.hash}`);
        }
        writeResume();
        document.dispatchEvent(new CustomEvent("ri:filters-applied"));
    };

    query?.addEventListener("input", () => apply());
    state?.addEventListener("change", () => apply());
    kind?.addEventListener("change", () => apply());
    for (const filter of extraFilters) filter.addEventListener("change", () => apply());
    journeyDateFrom?.addEventListener("change", () => apply());
    journeyDateTo?.addEventListener("change", () => apply());
    reset?.addEventListener("click", () => {
        if (query) query.value = "";
        if (state) state.value = "all";
        if (kind) kind.value = "all";
        for (const filter of extraFilters) filter.value = "all";
        if (journeyDateFrom) journeyDateFrom.value = "";
        if (journeyDateTo) journeyDateTo.value = "";
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

    const decisionLinks = [...document.querySelectorAll("[data-decision-link]")];
    for (const [index, link] of decisionLinks.entries()) {
        link.addEventListener("keydown", (event) => {
            let next = null;
            if (event.key === "ArrowDown" || event.key === "ArrowRight") next = Math.min(index + 1, decisionLinks.length - 1);
            if (event.key === "ArrowUp" || event.key === "ArrowLeft") next = Math.max(index - 1, 0);
            if (event.key === "Home") next = 0;
            if (event.key === "End") next = decisionLinks.length - 1;
            if (next !== null) {
                event.preventDefault();
                decisionLinks[next].focus();
            }
        });
    }

    const journeyLinks = [...document.querySelectorAll("[data-journey-link]")];
    for (const [index, link] of journeyLinks.entries()) {
        link.addEventListener("keydown", (event) => {
            let next = null;
            if (event.key === "ArrowDown" || event.key === "ArrowRight") next = Math.min(index + 1, journeyLinks.length - 1);
            if (event.key === "ArrowUp" || event.key === "ArrowLeft") next = Math.max(index - 1, 0);
            if (event.key === "Home") next = 0;
            if (event.key === "End") next = journeyLinks.length - 1;
            if (next !== null) {
                event.preventDefault();
                journeyLinks[next].focus();
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

    const decisionIndexLinks = [...document.querySelectorAll("[data-decision-index]")];
    const markSelectedDecision = (identifier) => {
        for (const decision of document.querySelectorAll("[data-decision-record]")) {
            decision.toggleAttribute("data-selected", decision.id === identifier);
        }
        for (const link of decisionIndexLinks) {
            if (link.hash.slice(1) === identifier) link.setAttribute("aria-current", "step");
            else link.removeAttribute("aria-current");
        }
    };

    const journeyIndexLinks = [...document.querySelectorAll("[data-journey-index]")];
    const markSelectedJourney = (identifier) => {
        const selected = document.getElementById(identifier);
        const selectedChapter = selected?.matches("[data-journey-chapter]")
            ? selected
            : selected?.closest("[data-journey-chapter]");
        for (const event of document.querySelectorAll("[data-journey-event]")) {
            event.toggleAttribute("data-selected", event.id === identifier);
        }
        for (const link of journeyIndexLinks) {
            if (link.hash.slice(1) === selectedChapter?.id) link.setAttribute("aria-current", "step");
            else link.removeAttribute("aria-current");
        }
    };

    const applyHashSelection = () => {
        const identifier = location.hash.slice(1);
        const selected = document.getElementById(identifier);
        const contextEntity = selected?.closest("[data-entity-id]");
        if (contextEntity) selectContextEntity(contextEntity);
        if (selected?.matches("[data-roadmap-quest]")) {
            markSelectedQuest(identifier);
            const evidence = selected.querySelector("[data-quest-evidence]");
            if (evidence) evidence.open = true;
            writeResume();
        } else if (selected?.matches("[data-decision-record]")) {
            markSelectedDecision(identifier);
            const evidence = selected.querySelector("[data-decision-evidence]");
            if (evidence) evidence.open = true;
            writeResume();
        } else if (selected?.matches("[data-journey-event]")) {
            markSelectedJourney(identifier);
            const evidence = selected.querySelector("[data-journey-evidence]");
            if (evidence) evidence.open = true;
            writeResume();
        } else if (selected?.matches("[data-journey-chapter]")) {
            markSelectedJourney(identifier);
            writeResume();
        }
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

    for (const details of document.querySelectorAll("[data-decision-evidence]")) {
        details.addEventListener("toggle", () => {
            if (!details.open) return;
            const decision = details.closest("[data-decision-record]");
            if (!decision) return;
            const next = new URL(location.href);
            next.hash = decision.id;
            history.replaceState(null, "", `${next.pathname}${next.search}${next.hash}`);
            markSelectedDecision(decision.id);
            const viewport = details.querySelector("[data-evidence-viewport]");
            evidenceWindows.find((entry) => entry.viewport === viewport)?.render();
            writeResume();
        });
    }

    for (const details of document.querySelectorAll("[data-journey-evidence]")) {
        details.addEventListener("toggle", () => {
            if (!details.open) return;
            const event = details.closest("[data-journey-event]");
            if (!event) return;
            const next = new URL(location.href);
            next.hash = event.id;
            history.replaceState(null, "", `${next.pathname}${next.search}${next.hash}`);
            markSelectedJourney(event.id);
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

    if ("IntersectionObserver" in window && decisionIndexLinks.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            const current = entries
                .filter((entry) => entry.isIntersecting && !entry.target.hidden)
                .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
            if (current && !location.hash) markSelectedDecision(current.target.id);
        }, { rootMargin: "-18% 0px -68%", threshold: [0.05, 0.25, 0.6] });
        for (const decision of document.querySelectorAll("[data-decision-record]")) {
            observer.observe(decision);
        }
    }

    if ("IntersectionObserver" in window && journeyIndexLinks.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            const current = entries
                .filter((entry) => entry.isIntersecting && !entry.target.hidden)
                .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
            if (current && !location.hash) markSelectedJourney(current.target.id);
        }, { rootMargin: "-18% 0px -68%", threshold: [0.05, 0.25, 0.6] });
        for (const chapter of document.querySelectorAll("[data-journey-chapter]")) {
            observer.observe(chapter);
        }
    }

    const compare = document.querySelector("[data-decision-compare]");
    const compareLeft = compare?.querySelector("[data-compare-left]");
    const compareRight = compare?.querySelector("[data-compare-right]");
    const compareOutput = compare?.querySelector("[data-compare-output]");
    const compareSwap = compare?.querySelector("[data-compare-swap]");
    const decisionRecords = new Map(
        [...document.querySelectorAll("[data-decision-record]")].map((record) => [
            record.dataset.decisionId,
            record,
        ]),
    );

    const renderComparison = ({ updateUrl = true } = {}) => {
        if (!compareLeft || !compareRight || !compareOutput) return;
        const left = decisionRecords.get(compareLeft.value);
        const right = decisionRecords.get(compareRight.value);
        compareOutput.replaceChildren();
        if (!left || !right || left === right) {
            const message = document.createElement("p");
            message.textContent = "Choose two different decisions to compare their projected lifecycle, authority, implementation, and impact.";
            compareOutput.append(message);
        } else {
            const table = document.createElement("table");
            const caption = document.createElement("caption");
            caption.textContent = "Projected decision comparison";
            table.append(caption);
            const head = document.createElement("thead");
            const headRow = document.createElement("tr");
            headRow.append(document.createElement("th"));
            for (const record of [left, right]) {
                const heading = document.createElement("th");
                heading.scope = "col";
                const link = document.createElement("a");
                link.href = `#${record.id}`;
                link.textContent = record.dataset.decisionTitle || "Untitled decision";
                heading.append(link);
                headRow.append(heading);
            }
            head.append(headRow);
            table.append(head);
            const body = document.createElement("tbody");
            const fields = [
                ["Lifecycle", "decisionStatus"],
                ["Implementation", "decisionImplementation"],
                ["Scope", "decisionScope"],
                ["Date", "decisionDateLabel"],
                ["Owner", "decisionOwnerLabel"],
                ["Domain", "decisionDomainLabel"],
                ["Affected component", "decisionComponentLabel"],
                ["Roadmap", "decisionRoadmapLabel"],
            ];
            for (const [label, field] of fields) {
                const row = document.createElement("tr");
                const heading = document.createElement("th");
                heading.scope = "row";
                heading.textContent = label;
                row.append(heading);
                for (const record of [left, right]) {
                    const cell = document.createElement("td");
                    cell.textContent = record.dataset[field] || "Not projected";
                    row.append(cell);
                }
                body.append(row);
            }
            table.append(body);
            compareOutput.append(table);
        }
        if (updateUrl) {
            const next = new URL(location.href);
            setOrDelete(next, "compare-left", compareLeft.value);
            setOrDelete(next, "compare-right", compareRight.value);
            history.replaceState(null, "", `${next.pathname}${next.search}${next.hash}`);
        }
    };

    if (compareLeft && compareRight) {
        const leftParameter = params.get("compare-left");
        const rightParameter = params.get("compare-right");
        if ([...compareLeft.options].some((option) => option.value === leftParameter)) {
            compareLeft.value = leftParameter;
        }
        if ([...compareRight.options].some((option) => option.value === rightParameter)) {
            compareRight.value = rightParameter;
        }
        compareLeft.addEventListener("change", () => renderComparison());
        compareRight.addEventListener("change", () => renderComparison());
        compareSwap?.addEventListener("click", () => {
            [compareLeft.value, compareRight.value] = [compareRight.value, compareLeft.value];
            renderComparison();
        });
        renderComparison({ updateUrl: false });
    }

    const journeyCompare = document.querySelector("[data-journey-compare]");
    const journeyCompareLeft = journeyCompare?.querySelector("[data-journey-compare-left]");
    const journeyCompareRight = journeyCompare?.querySelector("[data-journey-compare-right]");
    const journeyCompareOutput = journeyCompare?.querySelector("[data-journey-compare-output]");
    const journeyCompareSwap = journeyCompare?.querySelector("[data-journey-compare-swap]");
    const journeyChapters = new Map(
        [...document.querySelectorAll("[data-journey-chapter]")].map((chapter) => [
            chapter.dataset.journeyChapterId,
            chapter,
        ]),
    );

    const renderJourneyComparison = ({ updateUrl = true } = {}) => {
        if (!journeyCompareLeft || !journeyCompareRight || !journeyCompareOutput) return;
        const left = journeyChapters.get(journeyCompareLeft.value);
        const right = journeyChapters.get(journeyCompareRight.value);
        journeyCompareOutput.replaceChildren();
        if (!left || !right || left === right) {
            const message = document.createElement("p");
            message.textContent = "Choose two different chapters to compare their projected structure.";
            journeyCompareOutput.append(message);
        } else {
            const counts = (chapter) => {
                try { return JSON.parse(chapter.dataset.journeyCounts || "{}"); }
                catch { return {}; }
            };
            const leftCounts = counts(left);
            const rightCounts = counts(right);
            const table = document.createElement("table");
            const caption = document.createElement("caption");
            caption.textContent = "Projected chapter comparison; differences do not imply causality or productivity.";
            table.append(caption);
            const head = document.createElement("thead");
            const headRow = document.createElement("tr");
            headRow.append(document.createElement("th"));
            for (const chapter of [left, right]) {
                const heading = document.createElement("th");
                heading.scope = "col";
                const link = document.createElement("a");
                link.href = `#${chapter.id}`;
                link.textContent = chapter.dataset.journeyChapterTitle || "Untitled chapter";
                heading.append(link);
                headRow.append(heading);
            }
            head.append(headRow);
            table.append(head);
            const tableBody = document.createElement("tbody");
            const rows = [
                ["Time window", (chapter) => `${chapter.dataset.journeyStart || "Unknown"} → ${chapter.dataset.journeyEnd || "Unknown"}`],
                ["Release boundary", (chapter) => chapter.dataset.journeyBoundary || "Open chapter"],
                ["Events", (_, values) => values.events ?? 0],
                ["Linked quests", (_, values) => values.quests ?? 0],
                ["Linked decisions", (_, values) => values.decisions ?? 0],
                ["Commits", (_, values) => values.commits ?? 0],
                ["Merged pull requests", (_, values) => values.merged_pull_requests ?? 0],
                ["Checks", (_, values) => values.checks ?? 0],
                ["Failing states", (_, values) => values.failures ?? 0],
                ["Releases and deployments", (_, values) => values.deliveries ?? 0],
                ["Unclassified events", (_, values) => values.unclassified ?? 0],
            ];
            for (const [label, value] of rows) {
                const row = document.createElement("tr");
                const heading = document.createElement("th");
                heading.scope = "row";
                heading.textContent = label;
                row.append(heading);
                for (const [chapter, values] of [[left, leftCounts], [right, rightCounts]]) {
                    const cell = document.createElement("td");
                    cell.textContent = String(value(chapter, values));
                    row.append(cell);
                }
                tableBody.append(row);
            }
            table.append(tableBody);
            journeyCompareOutput.append(table);
        }
        if (updateUrl) {
            const next = new URL(location.href);
            setOrDelete(next, "journey-left", journeyCompareLeft.value);
            setOrDelete(next, "journey-right", journeyCompareRight.value);
            history.replaceState(null, "", `${next.pathname}${next.search}${next.hash}`);
        }
    };

    if (journeyCompareLeft && journeyCompareRight) {
        const leftParameter = params.get("journey-left");
        const rightParameter = params.get("journey-right");
        if ([...journeyCompareLeft.options].some((option) => option.value === leftParameter)) {
            journeyCompareLeft.value = leftParameter;
        }
        if ([...journeyCompareRight.options].some((option) => option.value === rightParameter)) {
            journeyCompareRight.value = rightParameter;
        } else if (journeyCompareRight.options.length > 1) {
            journeyCompareRight.selectedIndex = 1;
        }
        journeyCompareLeft.addEventListener("change", () => renderJourneyComparison());
        journeyCompareRight.addEventListener("change", () => renderJourneyComparison());
        journeyCompareSwap?.addEventListener("click", () => {
            [journeyCompareLeft.value, journeyCompareRight.value] = [journeyCompareRight.value, journeyCompareLeft.value];
            renderJourneyComparison();
        });
        renderJourneyComparison({ updateUrl: false });
    }

    const replayButton = document.querySelector("[data-journey-replay]");
    const replayScrubber = document.querySelector("[data-journey-scrubber]");
    const replayOutput = document.querySelector("[data-journey-replay-output]");
    const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
    let replayTimer = null;
    let replayEvents = [];

    const stopReplay = () => {
        if (replayTimer !== null) window.clearInterval(replayTimer);
        replayTimer = null;
        if (replayButton && !motionPreference.matches) replayButton.textContent = "Replay journey";
    };

    const setReplayPosition = (position, { scroll = false } = {}) => {
        if (!replayScrubber || !replayOutput || replayEvents.length === 0) return;
        const bounded = Math.max(0, Math.min(position, replayEvents.length - 1));
        replayScrubber.value = String(bounded + 1);
        for (const [index, event] of replayEvents.entries()) {
            event.dataset.replayState = index < bounded ? "past" : index === bounded ? "current" : "future";
        }
        const current = replayEvents[bounded];
        replayOutput.value = `${bounded + 1} of ${replayEvents.length} · ${current.dataset.journeyEventTitle || "Untitled event"}`;
        if (scroll) current.scrollIntoView({ block: "center", behavior: motionPreference.matches ? "auto" : "smooth" });
    };

    const syncReplayEvents = () => {
        stopReplay();
        replayEvents = [...document.querySelectorAll("[data-journey-event]:not([hidden])")];
        if (!replayButton || !replayScrubber || !replayOutput) return;
        replayScrubber.max = String(Math.max(1, replayEvents.length));
        replayScrubber.disabled = replayEvents.length === 0;
        replayButton.disabled = replayEvents.length === 0 || motionPreference.matches;
        replayButton.textContent = motionPreference.matches ? "Automatic replay disabled" : "Replay journey";
        if (replayEvents.length === 0) {
            replayOutput.value = "No visible events to replay";
            return;
        }
        replayScrubber.value = String(replayEvents.length);
        for (const event of replayEvents) event.removeAttribute("data-replay-state");
        replayOutput.value = `${replayEvents.length} visible events ready`;
    };

    replayScrubber?.addEventListener("input", () => {
        stopReplay();
        setReplayPosition(Number(replayScrubber.value) - 1, { scroll: true });
    });
    replayButton?.addEventListener("click", () => {
        if (motionPreference.matches || replayEvents.length === 0) return;
        if (replayTimer !== null) {
            stopReplay();
            return;
        }
        setReplayPosition(0, { scroll: true });
        replayButton.textContent = "Pause replay";
        replayTimer = window.setInterval(() => {
            const next = Number(replayScrubber?.value || 1);
            if (next >= replayEvents.length) {
                stopReplay();
                return;
            }
            setReplayPosition(next, { scroll: true });
        }, 900);
    });
    motionPreference.addEventListener?.("change", syncReplayEvents);
    document.addEventListener("ri:filters-applied", syncReplayEvents);

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
