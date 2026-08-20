/* Copyright 2026 Ego Hygiene */
/* SPDX-License-Identifier: MIT */

(() => {
    "use strict";

    const explorer = document.querySelector("[data-repository-explorer]");
    if (!explorer) {
        return;
    }

    const search = explorer.querySelector("[data-tree-search]");
    const root = explorer.querySelector("[data-tree-root]");
    const status = explorer.querySelector("[data-tree-status]");
    const empty = explorer.querySelector("[data-tree-empty]");
    const expand = explorer.querySelector("[data-tree-expand]");
    const collapse = explorer.querySelector("[data-tree-collapse]");
    const nodes = Array.from(explorer.querySelectorAll(".tree-node"));
    const directories = Array.from(explorer.querySelectorAll("[data-tree-directory]"));

    if (!search || !root || !status || !empty || !expand || !collapse) {
        return;
    }

    for (const details of directories) {
        details.dataset.initialOpen = details.open ? "true" : "false";
    }

    const immediateChildren = (node) => {
        const details = node.querySelector(":scope > details");
        if (!details) {
            return [];
        }
        const childList = details.querySelector(":scope > .tree-directory-body > .tree-children");
        return childList
            ? Array.from(childList.children).filter((child) =>
                  child.classList.contains("tree-node"),
              )
            : [];
    };

    const filterNode = (node, query) => {
        const children = immediateChildren(node);
        let descendantMatch = false;
        for (const child of children) {
            descendantMatch = filterNode(child, query) || descendantMatch;
        }
        const directMatch = node.dataset.search.includes(query);
        const visible = directMatch || descendantMatch;
        node.hidden = !visible;

        const details = node.querySelector(":scope > details");
        if (details && query && descendantMatch) {
            details.open = true;
        }
        return visible;
    };

    const restoreTree = () => {
        for (const node of nodes) {
            node.hidden = false;
        }
        for (const details of directories) {
            details.open = details.dataset.initialOpen === "true";
        }
        empty.hidden = true;
        status.textContent = `Showing all ${nodes.length} entries.`;
    };

    const applySearch = () => {
        const query = search.value.trim().toLocaleLowerCase();
        if (!query) {
            restoreTree();
            return;
        }

        const topLevelNodes = Array.from(root.children).filter((child) =>
            child.classList.contains("tree-node"),
        );
        for (const node of topLevelNodes) {
            filterNode(node, query);
        }
        const matches = nodes.filter((node) => node.dataset.search.includes(query)).length;
        empty.hidden = matches !== 0;
        status.textContent = matches === 1 ? "1 matching entry." : `${matches} matching entries.`;
    };

    let pendingFrame = 0;
    search.addEventListener("input", () => {
        window.cancelAnimationFrame(pendingFrame);
        pendingFrame = window.requestAnimationFrame(applySearch);
    });
    search.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && search.value) {
            search.value = "";
            restoreTree();
        }
    });
    expand.addEventListener("click", () => {
        for (const details of directories) {
            if (!details.closest(".tree-node").hidden) {
                details.open = true;
            }
        }
    });
    collapse.addEventListener("click", () => {
        for (const details of directories) {
            details.open = false;
        }
    });
})();
