// Configuration constants matching backend behavior
const IGNORABLE_SEGMENTS = new Set(['', '.', 'undefined', 'null']);
const FILE_SUFFIXES = ['-MAP.html', '-PRINT.html', '.html', '.htm'];

/**
 * Clean file suffixes, or return null if ignorable/empty.
 */
function cleanPathPart(part) {
    if (!part) return null;
    const trimmed = part.trim();

    if (IGNORABLE_SEGMENTS.has(trimmed)) {
        return null;
    }

    for (const suffix of FILE_SUFFIXES) {
        if (trimmed.endsWith(suffix)) {
            return null;
        }
    }

    return trimmed;
}

/**
 * Split path string, clean each segment, and remove sequential duplicates.
 */
function stepify(pathStr) {
    if (!pathStr || typeof pathStr !== 'string') return [];

    const parts = pathStr.trim().split('/');
    const cleaned = [];

    for (const part of parts) {
        const cleanedPart = cleanPathPart(part);
        if (cleanedPart) {
            if (cleaned.length === 0 || cleaned[cleaned.length - 1] !== cleanedPart) {
                cleaned.push(cleanedPart);
            }
        }
    }

    return cleaned;
}


 const TYPE_SEGMENT = { ward: 'WARDS', division: 'DIVS' };
 const TYPED_CHILD_INDEX = 4;

 /**
  * parts:     level-aligned steps, e.g. ['UNITED_KINGDOM','ENGLAND','SURREY','EAST_SURREY','GODSTONE']
  * typedNode: type ('ward' | 'division') of the node at index 4 in this path.
  */
 function pathify(parts, typedNode = 'ward') {
     if (!Array.isArray(parts) || parts.length === 0) {
         return "";
     }

     // Already typed? Don't insert a second segment.
     if (parts.some(p => Object.values(TYPE_SEGMENT).includes(p))) {
         return parts.join('/');
     }

     // Too shallow to have a typed child
     if (parts.length <= TYPED_CHILD_INDEX) {
         return parts.join('/');
     }

     const seg = TYPE_SEGMENT[typedNode];
     return [
         ...parts.slice(0, TYPED_CHILD_INDEX),
         ...(seg ? [seg] : []),
         ...parts.slice(TYPED_CHILD_INDEX),
     ].join('/');
 }

// Make stepify & pathify available globally
window.stepify = stepify;
window.pathify = pathify;


// WARDS / DIVS are grouping segments in the typed area tree: they are shown as
// headers but have no map of their own, so they never get an "All" map button.
// WARDS / DIVS are grouping segments in the typed area tree: they are shown as
// headers but have no map of their own, so they never get an "All" map button.
const TYPE_GROUPS = new Set(['WARDS', 'DIVS']);

window.renderTreeSelector = function (tree, options = {}) {
    const {
        containerId,
        emptyMessage = 'No items available',
        accordionId,
        allLabel = name => `All of ${name}`,
        createButton,
        rootPath,               // real keys descended through to reach `tree`
        showLeafValues = false  // render scalar/array leaves (e.g. task tags) too
    } = options;

    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '';

    if (!tree || typeof tree !== 'object' ||
        Object.keys(tree).length === 0) {
        container.innerHTML =
            `<div class="small text-muted p-2">${emptyMessage}</div>`;
        return;
    }

    const isPlainObj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
    const escapeHtml = s => String(s).replace(/[&<>"']/g, c => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));

    const acc = document.createElement('div');
    acc.className = 'accordion';
    acc.id = accordionId;

    let idCounter = 0;

    function renderLevel(node, parentElement, path = [], depth = 0) {
        if (!node || typeof node !== 'object') return;

        // Arrays of leaves become [name, null] entries so they render as buttons
        const entries = Array.isArray(node)
            ? node.map(v => [String(v), null])
            : Object.entries(node);

        entries.forEach(([name, children]) => {
            const currentPath = [...path, name];
            const isGroup = TYPE_GROUPS.has(name.toUpperCase());

            const hasChildren = showLeafValues
                ? (isPlainObj(children) && Object.keys(children).length > 0) ||
                  (Array.isArray(children) && children.length > 0)
                : isPlainObj(children) &&
                  Object.keys(children).length > 0 &&
                  Object.values(children).some(
                      val => typeof val === 'object' && val !== null
                  );

            const uniqueId = `${accordionId}-${idCounter++}`;

            // ---- Top level: Bootstrap accordion items ----
            if (depth === 0) {
                const item = document.createElement('div');
                item.className = 'accordion-item border-0 mb-1';

                item.innerHTML = `
                    <h2 class="accordion-header">
                        <button class="accordion-button collapsed py-2 shadow-none"
                                type="button"
                                data-bs-toggle="collapse"
                                data-bs-target="#${uniqueId}"
                                aria-expanded="false">
                            ${escapeHtml(name.replace(/_/g, ' '))}
                        </button>
                    </h2>
                    <div id="${uniqueId}" class="accordion-collapse collapse">
                        <div class="accordion-body p-0"></div>
                    </div>
                `;

                const body = item.querySelector('.accordion-body');

                if (!isGroup) {
                    createButton(
                        body, name, allLabel(name),
                        'fw-semibold', currentPath
                    );
                }

                if (hasChildren) {
                    renderLevel(children, body, currentPath, depth + 1);
                }

                parentElement.appendChild(item);
                return;
            }

            // ---- Nested levels ----
            const wrapper = document.createElement('div');
            wrapper.className = 'border-0';

            if (hasChildren) {
                const header = document.createElement('button');
                header.type = 'button';
                header.className =
                    'btn btn-sm w-100 text-start py-2 shadow-none';
                header.style.paddingLeft = `${1 + depth * 1.25}rem`;
                header.setAttribute('data-bs-toggle', 'collapse');
                header.setAttribute('data-bs-target', `#${uniqueId}`);
                header.setAttribute('aria-expanded', 'false');
                header.textContent = `▸ ${name.replace(/_/g, ' ')}`;

                const collapse = document.createElement('div');
                collapse.id = uniqueId;
                collapse.className = 'collapse';

                const list = document.createElement('div');
                list.className = 'list-group list-group-flush';

                if (!isGroup) {
                    createButton(
                        list, name, allLabel(name), '', currentPath
                    );
                }

                renderLevel(children, list, currentPath, depth + 1);

                collapse.appendChild(list);
                wrapper.appendChild(header);
                wrapper.appendChild(collapse);
            } else if (!isGroup) {
                // Leaf: show "L1 – Door knocking" when the value is a description
                const label = showLeafValues && typeof children === 'string' && children
                    ? `${name} – ${children}`
                    : name;

                createButton(wrapper, name, label, '', currentPath);
            }

            parentElement.appendChild(wrapper);
        });
    }

    // Start path: use the keys the caller actually descended through, so the
    // path and the tree can never drift apart. Fall back to the old
    // mapfile-based guess only if no rootPath was supplied.
    let startPath;
    if (Array.isArray(rootPath)) {
        startPath = [...rootPath];
    } else {
        startPath = typeof stepify === 'function'
            ? stepify(window.mapfile || '')
            : [];
        startPath.pop();
    }

    renderLevel(tree, acc, startPath);
    container.appendChild(acc);
};

function createMapButton(parentElement, nodeName, labelText, className, nodePath) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `btn btn-sm w-100 text-start py-1 px-3 ${className || ''}`;
    btn.textContent = labelText.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
    btn.onclick = async (e) => {
        e.preventDefault();
        e.stopPropagation();

        // nodePath may be an array (from renderTreeSelector) or a string
        const targetPath = Array.isArray(nodePath) ? nodePath.join('/') : String(nodePath);
        const leafNodeName = targetPath.split('/').pop();
        const prettyName = leafNodeName.replace(/_/g, ' ');
        const mapFilename = `${leafNodeName}-MAP.html`;
        const fetchPath = `${targetPath}/${mapFilename}`;

        const notLoaded = () => showDataNotLoaded(prettyName);

        try {
            const response = await fetch(`/transfer/${fetchPath}`, {
                method: 'GET',
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            if (!response.ok) return notLoaded();

            const data = await response.json();
            if (!data.success || !data.map_url) return notLoaded();

            const mapIframe = document.getElementById('iframe1') || document.querySelector('iframe');
            if (mapIframe) mapIframe.src = data.map_url;

            window.currentNodePath = targetPath;
            window.mapfile = fetchPath;

            const displayElement = document.getElementById('display-path');
            if (displayElement) displayElement.innerText = prettyName;
        } catch (error) {
            console.error("❌ Error setting node path on backend:", error);
            notLoaded();
        }
    };

    parentElement.appendChild(btn);
}

function showDataNotLoaded(areaName) {
    alert(
        `No map is available for ${areaName}.\n\n` +
        `The elector data for this area hasn't been loaded yet. ` +
        `Please import the elector data for ${areaName} and try again.`
    );
}




function createAreaButton(list, AreaCode, displayName, indentClass = '', nodePath) {
  // Typed Geo_index path is the unique id; fall back to the bare name if none is supplied
  const code = Array.isArray(nodePath) ? nodePath.join('/') : (nodePath || AreaCode);

  const button = document.createElement('button');
  button.type = 'button';
  button.className = `list-group-item list-group-item-action small ${indentClass}`;
  button.textContent = displayName;
  button.dataset.code = code;

  if (window.selectedArea === code) button.classList.add('active');

  button.addEventListener('click', () => {
    list.closest('.accordion')
        ?.querySelectorAll('.list-group-item')
        .forEach(b => b.classList.remove('active'));
    window.selectedArea = code;
    button.classList.add('active');
    syncAreaSelect();
  });

  list.appendChild(button);
}


function createTaskButton(list, taskCode, displayName, indentClass = '') {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `list-group-item list-group-item-action small ${indentClass}`;
  button.textContent = displayName;
  button.dataset.code = taskCode;

  if (window.selectedTask === taskCode) button.classList.add('active');

  button.addEventListener('click', () => {
    list.closest('.accordion')
        ?.querySelectorAll('.list-group-item')
        .forEach(b => b.classList.remove('active'));
    window.selectedTask = taskCode;
    button.classList.add('active');
    syncTaskSelect();
  });

  list.appendChild(button);
}




  function getTagsJson(electionTags) {
    const task_tags = {};
    const outcome_tags = {};

    Object.entries(electionTags || {}).forEach(([tag, description]) => {
        if (tag.startsWith("L")) {
            task_tags[tag] = description;
        } else if (tag.startsWith("M")) {
            outcome_tags[tag] = description;
        }
    });

    console.log("___Dash Task Tags", task_tags);
    console.log( "Outcome Tags:", outcome_tags);
    return { task_tags, outcome_tags };
}


/* ---------- Sync Helpers for Single Select ---------- */
window.selectedArea = null;
window.selectedTask = null;

function syncTaskSelect() {
  const sel = document.getElementById('activitySelect');
  if (!sel) return;

  const code = window.selectedTask;
  if (!code) {
    sel.replaceChildren();
    return;
}

  const label = code; // Replace with the task's descriptive label
  sel.replaceChildren(new Option(label, code, true, true));
  sel.value = code;
}

function syncAreaSelect() {
  const sel = document.getElementById('areaSelect');
  if (!sel) return;

  const code = window.selectedArea;
  if (!code) {
    sel.replaceChildren();
    return;
  }

  const lastName = code.split('/').pop().replace(/_/g, ' ');   // visible label only
  const opt = new Option(lastName, code, true, true);          // value stays the full path
  opt.title = code.replace(/_/g, ' ');                         // optional: full path on hover
  sel.replaceChildren(opt);
  sel.value = code;
}

window.initAccordionFromOptions = (tree, config = {}) => {
    const containerId  = config.containerId  || 'children-list';
    const accordionId  = config.accordionId  || 'election-accordion';
    const emptyMessage = config.emptyMessage || 'No sub-divisions available';
    const createButton = config.createButton || window.createMapButton;

    const renderEmpty = (msg = emptyMessage) =>
        window.renderTreeSelector?.({}, { containerId, accordionId, emptyMessage: msg, createButton });

    if (!tree || typeof tree !== 'object' || Object.keys(tree).length === 0) {
        renderEmpty();
        return;
    }

    const mapfile = window.mapfile;
    if (!mapfile || typeof stepify !== 'function') {
        console.error("❌ initAccordionFromOptions: window.mapfile is empty, so paths can't be built.");
        renderEmpty('Current area unknown');
        return;
    }

    const fullSteps = stepify(mapfile);
    if (fullSteps.length === 0) {
        console.error("❌ window.mapfile gave no path steps:", mapfile);
        renderEmpty('Current area unknown');
        return;
    }

    // The tree's own top-level key(s) define its root; find where that sits in mapfile
    const topKeys = Object.keys(tree);
    const rootIdx = fullSteps.findIndex(s =>
        topKeys.some(k => k.toUpperCase() === s.toUpperCase()));

    let currentTree = tree;
    let rootPath;

    if (rootIdx >= 0) {
        // Tree is wrapped at an ancestor (e.g. {SURREY: {...}}): descend its root once
        rootPath = fullSteps.slice(0, rootIdx);
        const rootKey = topKeys.find(k => k.toUpperCase() === fullSteps[rootIdx].toUpperCase());
        if (tree[rootKey] && typeof tree[rootKey] === 'object') {
            currentTree = tree[rootKey];
            rootPath.push(rootKey);
        }
    } else {
        // Tree is the current node's children: mapfile is the full prefix
        rootPath = [...fullSteps];
        console.log('Tree has no key on mapfile path; treating as children of', rootPath.join('/'));
    }

    console.log('mapfile:', mapfile, '→ rootPath:', rootPath,
                '| top-level items:', Object.keys(currentTree));

    const displayElement = document.getElementById('display-path');
    if (displayElement) {
        displayElement.innerText = fullSteps[fullSteps.length - 1].replace(/_/g, ' ');
    }

    if (typeof window.renderTreeSelector !== "function") {
        console.warn("⚠️ initAccordionFromOptions: window.renderTreeSelector is not available.");
        return;
    }

    window.renderTreeSelector(currentTree, {
        containerId,
        accordionId,
        emptyMessage,
        allLabel: (name) => name.replace(/_/g, ' '),
        createButton,
        rootPath
    });

    console.log(`✅ Initialized accordion for #${containerId} rooted at /${rootPath.join('/')}`);
};
