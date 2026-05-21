/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

// Remove the single quotes around the Jinja expression
var pack = window.flaskMessages ;

// Now you can loop through them or push them to your array
const pessages = [];
if (pack && pack.length > 0) {
    pack.forEach(msg => {
        pessages.push(msg);
        console.log("Flash Message:", msg);
    });
}



var iframeEl = document.getElementsByName('iframe1');

function bindEvent( element, eventName, eventHandler) {
 if (element.addEventListener){
     element.addEventListener(eventName, eventHandler, false);
 } else if (element.attachEvent) {
     element.attachEvent('on' + eventName, eventHandler);
 };
};

bindEvent( window, 'message', function (e) {
  pessages.pop();
  pessages.push(e.data);
  var ul = document.getElementById("logwin");
  var li = document.createElement("li");
  li.appendChild(document.createTextNode(e.data));
  if (ul) {
    ul.appendChild(li);
    console.log("✅ Successfully appended location row to UI.");
} else {
    // 💡 This prevents the 'Cannot read properties of null' crash on static sites!
    console.warn("ℹ️ UI container element was not found on this page layout. Location update skipped.");
}
  console.log("_____FlashPostedmessage: ",e.data);
});


var moveDown = function (msg, area, type) {
    window.parent.postMessage({ type: `Drilling down to ${type} level within ${area}`}, '*');

    const ul = parent.document.getElementById("logwin");
    if (ul) ul.scrollTop = ul.scrollHeight;
    window.location.assign(msg);
//    alert("Submitting to: " + msg);

};


var moveUp = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage({ type:"Moving up to "+ area + " "+ type+ " level "}, '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = ul.scrollHeight;

      };
var showMore = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage({ type: "Showing the "+type+ " level within "+ area}, '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = ul.scrollHeight;
      };

      /* When the user clicks on the button,
      toggle between hiding and showing the dropdown content */

// --- MOVE THESE TO MAP.JS ---

window.BAKED_DATA =
    window.BAKED_DATA ||
    (parent && parent.BAKED_DATA) ||
    [];

/* --- Top of map.js --- */
/* --- Top of map.js --- */
// 1. Map Handle
var fmap;



/**
 * Saves the global data object to browser storage.
 * @param {Object} data - The current BAKED_DATA object.
 */
 window.saveBakedData = function(data) {
     try {
         var parentWindow = window.parent || window;
         if (!Array.isArray(data)) data = [];

         const dataString = JSON.stringify(data);

         // 💾 THE STICKY NOTE: Keep a resilient local emergency backup
         localStorage.setItem('CANVASS_BAKED_DATA', dataString);
         parentWindow.BAKED_DATA = data;

         console.log("💾 Emergency local backup committed to Browser Storage.");
     } catch (e) {
         console.error("❌ Failed to commit local storage backup:", e);
     }
};

/**
 * Gathers un-synced entries out of local memory storage and drops them to the
 * backend server framework endpoint in a single batch query chain.
 *
 * @returns {Promise<boolean>} Resolves true if sync is clean or succeeds, false on network errors.
 */
window.syncBackend = function() {
    var parentWindow = window.parent || window;
    const eventLog = parentWindow.BAKED_DATA || [];

    // Filter down exclusively to operations missing a true synchronization check mark
    const unsynced = eventLog.filter(e => !e.synced);

    if (unsynced.length === 0) {
        console.log("ℹ️ No un-synced local changes found.");
        return Promise.resolve(true);
    }

    console.log(`🚀 Batch uploading ${unsynced.length} un-synced changes to server...`);

    // Match your original route string endpoint: '/upload_data'
    return fetch('/upload_data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ events: unsynced })
    })
    .then(res => {
        if (!res.ok) throw new Error("Network collection upload synchronization failed");

        // Mark only successfully uploaded elements as synced in our live global array
        unsynced.forEach(e => {
            e.synced = true;
        });

        // Re-stringify the updated log array and persist to local storage backup cache
        localStorage.setItem('CANVASS_BAKED_DATA', JSON.stringify(parentWindow.BAKED_DATA));
        console.log("🚀 Sync complete! Remote server updated and local cache synchronized.");

        // Clear warning indicators or toggle save button elements if present
        var deployBtn = document.getElementById('deploy-btn');
        if (deployBtn) deployBtn.disabled = true;

        return true;
    })
    .catch(err => {
        console.error("❌ Failed to push batch payload modifications to database container:", err);
        return false;
    });
};

/**
 * Loads the data back from storage on page load.
 */
 window.getBakedData = function() {
     try {

         const saved = localStorage.getItem('CANVASS_BAKED_DATA');

         if (saved) {
             const parsed = JSON.parse(saved);

             // enforce array model
             window.BAKED_DATA = Array.isArray(parsed) ? parsed : [];

             return window.BAKED_DATA;
         }

     } catch (e) {
         console.error("❌ Error loading:", e);
     }

     window.BAKED_DATA = window.BAKED_DATA || [];
     return window.BAKED_DATA;
 };

 window.__pendingRender = () => {
     const currentData = getBakedData();

     if (!Array.isArray(currentData)) {
         console.warn("⚠️ [__pendingRender] currentData is not an array. Aborting batch render.");
         return;
     }

     // 1. Gather only unique, valid region string identifiers from the event stream
     const uniqueRegionIds = new Set();

     currentData.forEach(ev => {
         if (ev && ev.region) {
             uniqueRegionIds.add(String(ev.region).trim().toUpperCase());
         }
     });

     console.log(`🔄 [PENDING RENDER] Executing batch update for unique regions:`, Array.from(uniqueRegionIds));

     // 2. Safely loop through the actual string literals instead of array indexes
     uniqueRegionIds.forEach(region_id => {
         if (!region_id || region_id === "UNDEFINED") return;
         window.plotTaskProgress(region_id, 'L1', 'walk');
     });
 };

 window.MAP_READY = false;
 window.__HYDRATED = false;

 function hydrateMapOnce() {
    if (window.__HYDRATED) return;
    window.__HYDRATED = true;

    const currentData = getBakedData();
    if (!Array.isArray(currentData) || currentData.length === 0) return;

    const tagRegistry = window.TAG_TO_GROUP_MAPPING || {};
    const tagCodes = Object.keys(tagRegistry);

    console.log("🎯 Hydrating map once (idempotent)");


    const uniqueRegions = [
        ...new Set(
            currentData
                .map(e => e.region)
                .filter(Boolean)
        )
    ];

    for (const region_id of uniqueRegions) {
        const codes = tagCodes.length ? tagCodes : ['L1'];

        for (const code of codes) {
            window.plotTaskProgress(region_id, code, 'walk');
        }
    }
}

(function startMapCatcher() {

    const findMap = () => {

        for (const key in window) {
            if (key.startsWith('map_') && window.L && window[key] instanceof window.L.Map) {

                window.fmap = window[key];

                const fmap = window.fmap;

                // -------------------------
                // POPUP REFRESH (SAFE)
                // -------------------------
                fmap.on('popupopen', function(e) {
                    const container = e.popup._contentNode;
                    const firstRow = container.querySelector('.canvass-row');

                    if (!firstRow || !window.plotTaskProgress) return;

                    const region_id = firstRow.getAttribute('data-region');

                    const tagsToUpdate = Object.keys(window.task_tags || {});
                    for (const tagCode of tagsToUpdate) {
                        window.plotTaskProgress(region_id, tagCode, 'walk');
                    }
                });

                fmap.invalidateSize();

                // -------------------------
                // SINGLE HYDRATION PASS
                // -------------------------
                window.MAP_READY = true;

                hydrateMapOnce();

                if (window.__pendingRender) {
                    window.__pendingRender();
                    window.__pendingRender = null;
                }

                return true;
            }
        }

        // iframe fallback
        const frame = document.getElementById('iframe1');

        if (frame?.contentWindow) {
            const frameWin = frame.contentWindow;

            for (const key in frameWin) {
                if (key.startsWith('map_') && frameWin.L && frameWin[key] instanceof frameWin.L.Map) {

                    window.fmap = frameWin[key];

                    const fmap = window.fmap;

                    fmap.on('popupopen', function(e) {
                        const container = e.popup._contentNode;
                        const firstRow = container.querySelector('.canvass-row');

                        if (!firstRow || !window.plotTaskProgress) return;

                        const region_id = firstRow.getAttribute('data-region');

                        for (const tagCode of Object.keys(window.task_tags || {})) {
                            window.plotTaskProgress(region_id, tagCode, 'walk');
                        }
                    });

                    fmap.invalidateSize();

                    window.MAP_READY = true;

                    hydrateMapOnce();

                    console.log("🎯 Map found in iframe:", key);

                    return true;
                }
            }
        }

        return false;
    };

    if (!findMap()) {
        const interval = setInterval(() => {
            if (findMap()) clearInterval(interval);
        }, 100);

        setTimeout(() => clearInterval(interval), 10000);
    }

})();


// 2. Calendar Toggle Logic
let toggleSent = false;
window.handleCalendarClick = function() {
    if (!toggleSent) {
        window.parent.postMessage({ type: "toggleView" }, "*");
        toggleSent = true;
        setTimeout(() => { toggleSent = false }, 500);
    }
};



// 3. Search Logic
async function searchMap() {
    const queryInput = document.getElementById("searchInput").value.trim();
    const fmap = window.fmap;


    if (!queryInput || !fmap) {
        console.warn("⚠️ Search cancelled: Missing query or map instance.");
        return;
    }

    const normalizedQuery = queryInput.toLowerCase();
    let found = false;

    console.log(`🔎 Starting search for: "${normalizedQuery}"`);

    // --- 1. POSTCODE SEARCH ---
    const postcodePattern = /^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$/i;
    if (postcodePattern.test(queryInput)) {
        console.log("📮 Postcode pattern detected. Fetching...");
        const cleanPostcode = queryInput.replace(/\s+/g, '');
        try {
            const res = await fetch(`http://api.getthedata.com/postcode/${cleanPostcode}`);
            const data = await res.json();
            if (data.status === "match" && data.data) {
                const { latitude, longitude } = data.data;
                console.log(`✅ Postcode match: ${latitude}, ${longitude}`);
                fmap.setView([latitude, longitude], 17);
                L.marker([latitude, longitude]).addTo(fmap).bindPopup(`<b>${queryInput.toUpperCase()}</b>`).openPopup();
                return;
            }
        } catch (err) { console.error("❌ Postcode API fail:", err); }
    }

    // --- 2. LAYER SEARCH ---
    fmap.eachLayer(function(layer) {
        if (found) return;

        let matchType = null;

        // A. Priority 1: region_id
        if (layer.feature && layer.feature.properties && layer.feature.properties.region_id) {
            const rid = String(layer.feature.properties.region_id).toLowerCase();
            if (rid.includes(normalizedQuery)) {
                console.log(`🎯 Match found in region_id: ${layer.feature.properties.region_id}`);
                matchType = 'region';
            }
        }

        // B. Priority 2: Tooltips
        if (!matchType && layer.getTooltip && layer.getTooltip()) {
            const content = String(layer.getTooltip().getContent());
            if (content.toLowerCase().includes(normalizedQuery)) {
                console.log(`📝 Match found in Tooltip text.`);
                matchType = 'tooltip';
            }
        }

        // C. Priority 3: Popups
        if (!matchType && layer.getPopup && layer.getPopup()) {
            const content = layer.getPopup().getContent();
            const plainText = (content instanceof HTMLElement) ? content.innerText : String(content);
            if (plainText.toLowerCase().includes(normalizedQuery)) {
                console.log(`💬 Match found in Popup content.`);
                matchType = 'popup';
            }
        }

        // --- 3. EXECUTE HIGHLIGHT & UI ---
        if (matchType) {
            found = true;
            console.log(`📍 Navigating to layer ID: ${layer._leaflet_id}`);

            const latlng = layer.getLatLng ? layer.getLatLng() : layer.getBounds().getCenter();
            fmap.setView(latlng, 17);

            // Universal Highlight Clone
            const highlightClone = L.geoJson(layer.toGeoJSON(), {
                style: {
                    color: '#000000',
                    fillColor: '#000000',
                    weight: 7,
                    fillOpacity: 0.4,
                    interactive: false
                }
            }).addTo(fmap);
            if (highlightClone.bringToFront) highlightClone.bringToFront();

            if (matchType === 'popup' || layer.getPopup()) {
                layer.openPopup();
                if (matchType === 'popup') {
                    console.log("🖋️ Highlighting specific row in popup...");
                    setTimeout(() => {
                        const elements = document.querySelectorAll('.leaflet-popup-content td, .leaflet-popup-content div');
                        elements.forEach(el => {
                            if (el.innerText.toLowerCase().includes(normalizedQuery)) {
                                const row = el.closest('tr') || el.closest('li') || el;
                                row.style.outline = "3px solid black";
                                row.style.outlineOffset = "-3px";
                                row.style.backgroundColor = "rgba(0, 0, 0, 0.05)";
                                layer.once('popupclose', () => {
                                    row.style.outline = "none";
                                    row.style.backgroundColor = "";
                                });
                            }
                        });
                    }, 50);
                }
            } else if (layer.getTooltip()) {
                layer.openTooltip();
            }

            const removeClone = () => {
                if (fmap.hasLayer(highlightClone)) {
                    console.log("🗑️ Cleanup: Removing black highlight clone.");
                    fmap.removeLayer(highlightClone);
                }
            };
            fmap.once('click', removeClone);
            layer.once('popupclose', removeClone);
            layer.once('tooltipclose', removeClone);
        }
    });

    if (!found) {
        console.warn(`❌ No results found for "${queryInput}"`);
        alert("No matching Region ID or street found.");
    }
}

window.updateRowAppearance = function(row, count, max) {
    if (!row) return;

    if (count >= max && max > 0) {
        row.style.backgroundColor = "#28a745"; // Green
        row.style.color = "#ffffff";
    } else if (count > 0) {
        row.style.backgroundColor = "#ffcc00"; // Yellow
        row.style.color = "#000000";
    } else {
        // CRITICAL: This resets the row when switching to an unvoted house
        row.style.backgroundColor = "";
        row.style.color = "#ffffff";
    }

    // Force all text to respect the new background
    row.querySelectorAll('td, b, i, span').forEach(el => {
        el.style.color = "inherit";
    });
};


function deriveState(events) {

    const state = {};

    for (const e of events) {

        state[e.uiScope] ??= {};
        state[e.uiScope][e.region] ??= {};
        state[e.uiScope][e.region][e.street] ??= {};
        state[e.uiScope][e.region][e.street][e.house] ??= { tags: {} };

        state[e.uiScope][e.region][e.street][e.house].tags[e.code] = e.value;
    }

    return state;
}

window.incrementVoteCount = function(btn) {
    var row = btn.closest('.canvass-row');
    if (!row) return;

    var count = parseInt(btn.getAttribute('data-count')) || 0;
    var max = parseInt(btn.getAttribute('data-max')) || 1;
    var viSel = row.querySelector('.vi-selector');
    var unitSel = row.querySelector('.unit-selector');

    if (!viSel || !unitSel) return;

    // Cycle or increment the vote count local tracking asset
    count = count >= max ? 0 : count + 1;
    btn.setAttribute('data-count', count);
    btn.innerText = count + '/' + max;

    // Attach exclusively to parent master storage container
    var parentWindow = window.parent || window;
    if (!parentWindow.BAKED_DATA) parentWindow.BAKED_DATA = [];

    parentWindow.BAKED_DATA.push({
        type: 'vi',
        uiScope: row.getAttribute('data-scope'),
        region: row.getAttribute('data-region'),
        street: row.getAttribute('data-street'),
        house: unitSel.value,
        vi: viSel.value,
        votes: count,
        timestamp: Date.now(),
        synced: false
    });

    // Toggle save button state to remind them there are un-deployed adjustments
    var deployBtn = document.getElementById('deploy-btn');
    if (deployBtn) deployBtn.disabled = false;
};

window.handleTagClick = function(span, uiScope = 'walk') {
    const isInactive = span.classList.contains('tag-inactive');
    const newValue = isInactive ? 'y' : 'n';
    const code = span.getAttribute('data-code');

    const row = span.closest('.canvass-row') || span.closest('tr');
    if (!row) return;

    const region = row.dataset.region;
    const street = row.dataset.street;

    // Get the popup container/document context
    const doc = row.ownerDocument;
    const sel = row.querySelector('.unit-selector');

    // 1. Calculate specific Street Weight
    const streetRows = doc.querySelectorAll(`.canvass-row[data-region="${region}"][data-street="${street}"]`);
    const streetWeight = sel ? sel.options.length : streetRows.length;

    // 2. Calculate global Region Weight (Total houses in the entire popup)
    let regionWeight = 0;
    const countedStreetsInRegion = new Set();
    const allRowsInRegion = doc.querySelectorAll(`.canvass-row[data-region="${region}"]`);

    allRowsInRegion.forEach(r => {
        const sKey = r.getAttribute('data-street');
        if (!sKey || countedStreetsInRegion.has(sKey)) return;
        countedStreetsInRegion.add(sKey);

        const sSel = r.querySelector('.unit-selector');
        const sRows = doc.querySelectorAll(`.canvass-row[data-region="${region}"][data-street="${sKey}"]`);
        regionWeight += sSel ? sSel.options.length : sRows.length;
    });

    const house = sel?.value;
    if (!region || !street || !house) return;

    // UI Updates
    span.classList.toggle('tag-active', newValue === 'y');
    span.classList.toggle('tag-inactive', newValue === 'n');
    span.innerText = newValue;

    // Write logs straight up to global parent window memory space
    var parentWindow = window.parent || window;
    parentWindow.BAKED_DATA ||= [];
    parentWindow.BAKED_DATA.push({
        type: 'tag',
        ts: Date.now(),
        uiScope,
        region,
        street,
        house,
        code,
        value: newValue,
        streetWeight: streetWeight,
        regionWeight: regionWeight,
        synced: false
    });

    // Keep map progression charting if necessary
    if (typeof parentWindow.plotTaskProgress === 'function') {
        parentWindow.plotTaskProgress(region, code, uiScope);
    } else if (typeof plotTaskProgress === 'function') {
        plotTaskProgress(region, code, uiScope);
    }

    // Toggle save button state to remind them there are un-deployed adjustments
    var deployBtn = document.getElementById('deploy-btn');
    if (deployBtn) deployBtn.disabled = false;
};

window.updateTagToggles = function(selector, uiScope = 'walk') {
    const row = selector.closest('.canvass-row') || selector.closest('tr');
    if (!row) return;

    const region = row.dataset.region;
    const street = row.dataset.street;
    const house = selector.value;

    // 1. EXTRACT BASELINE TRUTH FROM THE ELECTOR ROW DATA
    const baselineTagsString = row.dataset.tags || '';

    // Parse the baseline (e.g., "L1,L2" becomes a Set or an array of active codes)
    const baselineActiveCodes = baselineTagsString.split(',')
        .map(t => t.trim().toUpperCase())
        .filter(Boolean);

    // Initialize our tracking truth map with the baseline defaults ('y')
    const finalComputedTags = {};
    baselineActiveCodes.forEach(code => {
        finalComputedTags[code] = 'y';
    });

    // 2. FIXED CONTEXT LAYER: Read event logs directly from parent storage array
    const parentWindow = window.parent || window;
    const events = parentWindow.BAKED_DATA || [];
    const relevantEvents = events.filter(e =>
        e.type === 'tag' &&
        e.uiScope === uiScope &&
        e.region === region &&
        e.street === street &&
        e.house === house
    );

    // 3. LAYER LOG OVERRIDES: Chronologically apply log updates over the baseline
    relevantEvents.forEach(e => {
        if (e.code) {
            finalComputedTags[e.code.toUpperCase()] = e.value;
        }
    });

    // 4. PRECISION UI TARGETING
    row.querySelectorAll('.tag-toggle').forEach(span => {
        const code = span.dataset.code ? span.dataset.code.toUpperCase() : '';
        if (!code) return;

        // If it's not in the baseline AND not in the logs, it defaults to 'n'
        const hasHistory = finalComputedTags.hasOwnProperty(code);
        const val = hasHistory ? finalComputedTags[code] : 'n';

        // 🌟 FIXED LOGIC COMPARISON: Force clean lower-case match check to align with UI text blocks
        if (span.innerText.trim().toLowerCase() !== val.toLowerCase()) {
            span.classList.toggle('tag-active', val === 'y');
            span.classList.toggle('tag-inactive', val !== 'y');
            span.innerText = val;
        }
    });
};

window.closePopupContainerModal = function() {
  console.log(`🔄 [POPUP CLOSE] uploading Baked data to server`);
    window.syncBackend().then(success => {
        if (success) {
            hideModalDOMElement(); // Sync cleared, close down safely
        } else {
            if (confirm("Warning: Changes could not sync to server. Close anyway?")) {
                hideModalDOMElement();
            }
        }
    });
}

window.replayLocalBakedDataForPopup = function(popupDocument) {
    const doc = popupDocument || document;

    // 1. Dynamically read the environment from the first row in the popup
    const firstRow = doc.querySelector('.canvass-row');
    if (!firstRow) {
        console.warn("⚠️ [REPLAY] Aborting. No '.canvass-row' elements found in target popup DOM.");
        return;
    }

    const currentRegion = String(firstRow.dataset.region || '').trim().toUpperCase();
    const currentScope = firstRow.dataset.scope || 'walk';

    if (!currentRegion) {
        console.warn("⚠️ [REPLAY] Aborting. Could not auto-detect data-region from popup elements.");
        return;
    }

    // 2. Fetch the transaction logs from the global storage engine
    const parentWindow = window.parent || window;
    if (typeof parentWindow.getBakedData !== 'function') {
        console.warn("⚠️ [REPLAY] Aborting. parentWindow.getBakedData function is not available.");
        return;
    }

    const localLogs = parentWindow.getBakedData() || [];
    console.log(`🔄 [POPUP REPLAY] Scanning local transaction ledger for Region: ${currentRegion} [Scope: ${currentScope}]`);

    // 3. Scan ledger to paint overrides onto the HTML view
    localLogs.forEach(ev => {
        if (!ev) return;

        // Guard: Verify event belongs to this scope and region
        if (ev.uiScope !== currentScope) return;
        if (String(ev.region).trim().toUpperCase() !== currentRegion) return;

        // Locate targeted street row in this specific popup document
        const targetRow = doc.querySelector(`.canvass-row[data-street="${ev.street}"]`);
        if (!targetRow) return;

        // -------------------------------------------------
        // CASE A: Replay Tag Overrides ('y' or 'n')
        // -------------------------------------------------
        if (ev.type === 'tag') {
            const btn = targetRow.querySelector(`.tag-toggle[data-code="${ev.code}"]`);
            if (btn) {
                const isActive = (ev.value === 'y');
                btn.classList.toggle('tag-active', isActive);
                btn.classList.toggle('tag-inactive', !isActive);
                btn.innerText = ev.value;
                console.log(`   ⚡ [REPLAY TAG] Applied: ${ev.street} | Code: ${ev.code} -> ${ev.value}`);
            }
        }

        // -------------------------------------------------
        // CASE B: Replay Voting Intentions (VI)
        // -------------------------------------------------
        else if (ev.type === 'vi') {
            const viSel = targetRow.querySelector('.vi-selector');
            if (viSel) {
                viSel.value = ev.value || '';
            }
            const voteBtn = targetRow.querySelector('.vote-btn');
            if (voteBtn && ev.votes !== undefined) {
                const maxVotes = voteBtn.getAttribute('data-max') || 1;
                voteBtn.setAttribute('data-count', ev.votes);
                voteBtn.innerText = `${ev.votes}/${maxVotes}`;
                console.log(`   ⚡ [REPLAY VI] Applied: ${ev.street} -> ${ev.votes} Votes`);
            }
        }
    });
};



window.updateMarkerStatus = function(region_id, uiScope = 'walk') {

    if (!region_id) return;

    // -------------------------------------------------
    // 1️⃣ DERIVE STATE FROM EVENTS
    // -------------------------------------------------
    const events = window.BAKED_DATA || [];

    const state = {};

    for (const e of events) {

        if (e.uiScope !== uiScope) continue;
        if (e.region !== region_id) continue;

        state[e.street] ??= {};
        state[e.street][e.house] ??= {
            votes: 0
        };

        if (typeof e.votes === 'number') {
            state[e.street][e.house].votes = e.votes;
        }
    }

    // -------------------------------------------------
    // 2️⃣ COUNT COMPLETED UNITS
    // -------------------------------------------------
    let completedUnits = 0;

    Object.values(state).forEach(street => {
        Object.values(street).forEach(house => {

            if ((house.votes || 0) > 0) {
                completedUnits++;
            }
        });
    });

    // -------------------------------------------------
    // 3️⃣ GET EXPECTED HOUSE COUNT (FROM MAP)
    // -------------------------------------------------
    let expectedHouses = 0;

    const activeMap =
        window.fmap ||
        parent.fmap ||
        document.getElementById('iframe1')?.contentWindow?.fmap;

    if (!activeMap) return;

    activeMap.eachLayer(layer => {
        const props = layer.feature?.properties;
        if (props?.region_id === region_id) {
            expectedHouses = props.expected_houses || 0;
        }
    });

    // -------------------------------------------------
    // 4️⃣ COLOR LOGIC
    // -------------------------------------------------
    const healthColor =
        (expectedHouses > 0 && completedUnits >= expectedHouses)
            ? "#28a745"
            : (completedUnits > 0 ? "#ffcc00" : null);

    // -------------------------------------------------
    // 5️⃣ UPDATE LABEL
    // -------------------------------------------------
    const labelSpan = document.getElementById(`label-${region_id}`);

    if (labelSpan && healthColor) {
        labelSpan.style.background = healthColor;
        labelSpan.style.color = "white";
    }

    // -------------------------------------------------
    // 6️⃣ UPDATE POLYGONS
    // -------------------------------------------------
    activeMap.eachLayer(layer => {

        const props = layer.feature?.properties;

        if (props?.region_id === region_id && healthColor) {

            layer.setStyle({
                fillColor: healthColor,
                fillOpacity: 0.8
            });
        }
    });
};
// map.js

function deriveState(events) {

    const state = {};

    for (const e of events) {

        state[e.uiScope] ??= {};
        state[e.uiScope][e.region] ??= {};
        state[e.uiScope][e.region][e.street] ??= {};
        state[e.uiScope][e.region][e.street][e.house] ??= { tags: {} };

        state[e.uiScope][e.region][e.street][e.house].tags[e.code] = e.value;
    }

    return state;
}


window.plotTaskProgress = function (
    region_id,
    targetTag = 'L1',
    uiScope = 'walk'
) {
    console.group(`🏗️ FLAT-EVENT PROGRESS MODEL: ${region_id} [${targetTag}]`);

    const activeMap = window.fmap || parent.fmap;
    const Leaflet = window.L || parent.L;
    const cleanId = String(region_id).trim().toUpperCase();
    const isViTarget = targetTag === 'VI';

    // Try to find open popup elements in the DOM
    const doc = document.getElementById('iframe1')?.contentWindow?.document || document;
    const rows = doc.querySelectorAll(`.canvass-row[data-region="${cleanId}"]`);

    let totalHouses = 0;
    let completedHouses = 0;

    // -----------------------------------------------------------------
    // CONDITION A: Popup is OPEN (Scrape live DOM elements)
    // -----------------------------------------------------------------
    if (rows.length > 0) {
        console.log("📊 Popup is open. Calculating opacity from live DOM elements...");
        const countedStreets = new Set();

        rows.forEach(row => {
            const street = row.getAttribute('data-street');
            if (!street || countedStreets.has(street)) return;
            countedStreets.add(street);

            const streetRows = doc.querySelectorAll(
                `.canvass-row[data-region="${cleanId}"][data-street="${street}"]`
            );

            const firstRow = streetRows[0];
            const sel = firstRow?.querySelector('.unit-selector');
            const streetWeight = sel ? sel.options.length : streetRows.length;

            totalHouses += streetWeight;

            let streetIsActive = false;
            streetRows.forEach(r => {
                if (isViTarget) {
                    // 🗳️ VI Live Check: Is there a vote recorded on the button text or value asset attribute?
                    const voteBtn = r.querySelector('.vote-count-btn');
                    const voteCount = parseInt(voteBtn?.dataset.count || '0');
                    if (voteCount > 0) {
                        streetIsActive = true;
                    }
                } else {
                    // 🏷️ Standard task tag active check
                    if (r.querySelector(`.tag-toggle[data-code="${targetTag}"].tag-active`)) {
                        streetIsActive = true;
                    }
                }
            });

            if (streetIsActive) {
                completedHouses += streetWeight;
            }
        });
    }
    // -----------------------------------------------------------------
    // CONDITION B: Popup is CLOSED (Parse flat ledger arrays)
    // -----------------------------------------------------------------
    else {
        console.log("💾 Popup is closed. Calculating opacity via baked region weights...");

        const eventLog = window.BAKED_DATA || [];

        let bakedRegionCeiling = 0;
        const streetWeightRegistry = {};
        const streetActiveHouses = {};

        // Chronological ledger scan
        eventLog.forEach(ev => {
            if (ev.uiScope !== uiScope) return;
            if (String(ev.region).trim().toUpperCase() !== cleanId) return;

            const street = ev.street;
            const house = ev.house;

            if (ev.streetWeight) streetWeightRegistry[street] = ev.streetWeight;
            if (ev.regionWeight) bakedRegionCeiling = ev.regionWeight;

            if (!streetActiveHouses[street]) {
                streetActiveHouses[street] = new Set();
            }

            // 🛠️ ALIGNED LEDGER PARSING LOGIC:
            // Since your app now logs explicitly explicit 'tag' structures for VI updates,
            // we consolidate checking here to look purely at target validation flags.
            if (ev.type === 'tag') {
                if (ev.code === targetTag) {
                    if (ev.value === 'y') {
                        streetActiveHouses[street].add(house);
                    } else if (ev.value === 'n') {
                        streetActiveHouses[street].delete(house);
                    }
                }
            }
            // Fallback safety net: if historical records only have type 'vi' logs with vote properties
            else if (isViTarget && ev.type === 'vi' && ev.votes !== undefined) {
                const voteValue = parseInt(ev.votes || '0');
                if (voteValue > 0) {
                    streetActiveHouses[street].add(house);
                } else {
                    streetActiveHouses[street].delete(house);
                }
            }
        });

        for (const street in streetActiveHouses) {
            const streetIsActive = streetActiveHouses[street].size > 0;
            if (streetIsActive) {
                const streetWeight = streetWeightRegistry[street] || 1;
                completedHouses += streetWeight;
            }
        }

        totalHouses = bakedRegionCeiling;

        if (totalHouses === 0 && completedHouses > 0) {
            for (const street in streetWeightRegistry) {
                totalHouses += streetWeightRegistry[street];
            }
        }
    }

    // -------------------------------------------------
    // 2️⃣ FINAL OPACITY FORMULA FLUSH
    // -------------------------------------------------
    const finalOpacity = totalHouses > 0 ? 0.8 * (completedHouses / totalHouses) : 0;

    console.log("📐 OPACITY ANALYSIS METRICS:", {
        region: cleanId,
        totalHouses,
        completedHouses,
        calculatedOpacity: finalOpacity
    });

    // -------------------------------------------------
    // 3️⃣ LAYER TARGET GROUP DISCOVERY
    // -------------------------------------------------
    const findBucket = () => {
        const mapWin = document.getElementById('iframe1')?.contentWindow || window;
        for (const key in mapWin) {
            if (!key.startsWith("layer_control_")) continue;
            const layers = mapWin[key].overlays || mapWin[key]._layers;
            for (const name in layers) {
                if (name.includes(`[${targetTag}]`)) {
                    return layers[name].layer || layers[name];
                }
            }
        }
        return null;
    };

    const targetGroup = findBucket();
    if (!targetGroup) {
        console.warn(`❌ Target Layer Control Overlay bucket missing for [${targetTag}].`);
        console.groupEnd();
        return;
    }

    // -------------------------------------------------
    // 4️⃣ APPLY OPACITY / UPDATE EXISTING GHOST
    // -------------------------------------------------
    const ghostId = `ghost_${targetTag}_${cleanId}`;
    let ghost = null;

    targetGroup.eachLayer(l => {
        if (l.ghost_id === ghostId) ghost = l;
    });

    if (ghost) {
        ghost.setStyle({ fillOpacity: finalOpacity });
        console.log(`♻️ Refreshed opacity style for ghost: ${ghostId}`);
        console.groupEnd();
        return;
    }

    // -------------------------------------------------
    // 5️⃣ GEOMETRY STRUCTURAL LOOKUP (🏎️ Fast Index Upgrade)
    // -------------------------------------------------
    const mapWin = document.getElementById('iframe1')?.contentWindow || window;
    const cache = mapWin.regionLayerCache || window.regionLayerCache || {};

    const targetVectorLayer = cache[cleanId];
    let geometry = null;

    if (targetVectorLayer && targetVectorLayer.feature?.geometry) {
        geometry = targetVectorLayer.feature.geometry;
    }

    if (!geometry) {
        console.log(`ℹ️ Skipping: Region ID ${cleanId} is outside current map view.`);
        console.groupEnd();
        return;
    }

    // -------------------------------------------------
    // 6️⃣ INSTANTIATE NEW LAYER GHOST ENTITY
    // -------------------------------------------------
    const poly = Leaflet.geoJSON(geometry, {
        pane: 'overlayPane',
        style: {
            color: "transparent",
            fillColor: targetTag === 'VI' ? "#800080" : "#333", // Simplified color matching rule
            fillOpacity: finalOpacity,
            interactive: false
        }
    });

    poly.is_ghost = true;
    poly.ghost_id = ghostId;

    targetGroup.addLayer(poly);

    if (!activeMap.hasLayer(targetGroup)) {
        activeMap.removeLayer(poly);
    }

    console.log(`✨ Ghost created via fast lookup index map: ${ghostId}`);
    console.groupEnd();
};

/**
 * Synchronizes a freshly rendered street list row with un-synced BAKED_DATA overrides
 * and runs standard startup layout calculations.
 *
 * @param {HTMLSelectElement} sel - The element (.unit-selector) inside the row
 * @param {string} scope - The active canvas scope ('walk', 'drive', etc.)
 */
window.initializeStreetRowState = function(sel, scope) {
    var parentWindow = window.parent || window;
    var row = sel.closest('.canvass-row');
    if (!row) return;

    // 1. Intercept state with un-synced BAKED_DATA local memory updates
    if (parentWindow.BAKED_DATA && Array.isArray(parentWindow.BAKED_DATA)) {
        var currentUnit = sel.value;
        var streetName = row.getAttribute('data-street');
        var regionId = row.getAttribute('data-region');

        // Scan backward through history to pick up the absolute newest action
        for (var i = parentWindow.BAKED_DATA.length - 1; i >= 0; i--) {
            var log = parentWindow.BAKED_DATA[i];
            if (log.type === 'vi' &&
                String(log.uiScope) === String(scope) &&
                String(log.region) === String(regionId) &&
                String(log.street) === String(streetName) &&
                String(log.house) === String(currentUnit)) {

                // Align selector dropdown
                var viSel = row.querySelector('.vi-selector');
                if (viSel) {
                    viSel.value = log.vi;
                }

                // Align live button metrics
                var voteBtn = row.querySelector('.vote-btn');
                if (voteBtn) {
                    var maxVal = voteBtn.getAttribute('data-max') || 1;
                    voteBtn.setAttribute('data-count', log.votes);
                    voteBtn.innerText = log.votes + '/' + maxVal;
                }
                break;
            }
        }
    }

    // 2. Fallback execution of standard structural style handlers
    if (typeof parentWindow.loadHouseData === 'function') parentWindow.loadHouseData(sel);
    if (typeof parentWindow.refreshDropdownColors === 'function') parentWindow.refreshDropdownColors(sel);
    if (typeof parentWindow.updateTagToggles === 'function') parentWindow.updateTagToggles(sel, scope);

    // 3. Render the target indicators
    if (typeof parentWindow.refreshRowVoteBadge === 'function') {
        parentWindow.refreshRowVoteBadge(row);
    }
};

// 🌟 SHARED LOCAL HANDLER FOR DYNAMIC PY-BAKED COUNTS
window.refreshRowVoteBadge = function(rowElement){
    if (!rowElement) return;
    var unitSel = rowElement.querySelector('.unit-selector');
    var viSel = rowElement.querySelector('.vi-selector');
    var btn = rowElement.querySelector('.vote-btn');
    if (!unitSel || !viSel || !btn) return;

    var currentUnit = unitSel.value;
    var currentVi = viSel.value ? viSel.value.toUpperCase() : "";

    // 1. Re-read max capacity directly from the selected option template metadata
    var selectedOpt = unitSel.options[unitSel.selectedIndex];
    var maxVotes = selectedOpt ? (selectedOpt.getAttribute('data-max') || 1) : 1;

    // 2. Identify the matching context fields out of the HTML row parameters
    var streetName = rowElement.getAttribute('data-street');
    var scope = rowElement.getAttribute('data-scope') || 'walk';
    var regionId = rowElement.getAttribute('data-region');

    var count = 0;
    var foundInFreshLogs = false;

    // 3. SCAN EVENT LOG FROM NEWEST TO OLDEST FOR OVERRIDES
    if (window.BAKED_DATA && Array.isArray(window.BAKED_DATA)) {
        for (var i = window.BAKED_DATA.length - 1; i >= 0; i--) {
            var log = window.BAKED_DATA[i];

            if (log.type === 'vi' &&
                String(log.uiScope) === String(scope) &&
                String(log.region) === String(regionId) &&
                String(log.street) === String(streetName) &&
                String(log.house) === String(currentUnit) &&
                String(log.vi).toUpperCase() === String(currentVi)) {

                count = parseInt(log.votes) || 0;
                foundInFreshLogs = true;
                break;
            }
        }
    }

    // 4. FALLBACK: Use Python's pre-baked database state if no user log edits exist
    if (!foundInFreshLogs) {
        var activeVotesDb = {};
        try {
            activeVotesDb = JSON.parse(rowElement.getAttribute('data-active-votes-db') || '{}');
        } catch(e) {
            console.error("Failed to parse row data-active-votes-db", e);
        }

        // Case-insensitive key checks against the pre-baked dictionary layout
        if (activeVotesDb[currentUnit]) {
            for (var key in activeVotesDb[currentUnit]) {
                if (key.toUpperCase() === currentVi) {
                    count = activeVotesDb[currentUnit][key];
                    break;
                }
            }
        }
    }

    // 5. Update UI elements
    btn.setAttribute('data-count', count);
    btn.setAttribute('data-max', maxVotes);
    btn.innerText = count + '/' + maxVotes;
};

/**
 * Automatically recalculates and updates the strongest VI and vote counts
 * when a user changes the house unit dropdown selection.
 *
 * @param {HTMLSelectElement} unitSel - The active .unit-selector element
 */
window.handleUnitChangeVIUpdate = function(unitSel) {
    var row = unitSel.closest('.canvass-row');
    if (!row) return;

    var selectedUnit = unitSel.value;
    var viSel = row.querySelector('.vi-selector');
    var voteBtn = row.querySelector('.vote-btn');
    if (!viSel || !voteBtn) return;

    // 1. Grab the raw house stats dump out of the row attribute
    var rawDb = row.getAttribute('data-active-votes-db');
    var activeVotesDb = {};
    try {
        if (rawDb) activeVotesDb = JSON.parse(rawDb);
    } catch (e) {
        console.error("❌ Failed to parse data-active-votes-db attribute:", e);
    }

    var chosenViCode = "";
    var currentVotes = 0;
    var maxVotes = parseInt(unitSel.options[unitSel.selectedIndex].getAttribute('data-max')) || 1;

    // 2. Scan the parsed dataset map for the newly selected house unit
    var houseVotes = activeVotesDb[selectedUnit] || {};
    var codes = Object.keys(houseVotes);

    if (codes.length > 0) {
        // Find the voting code targeting the highest metric tally integer
        chosenViCode = codes.reduce(function(a, b) {
            return (parseInt(houseVotes[a] || 0) >= parseInt(houseVotes[b] || 0)) ? a : b;
        });
        chosenViCode = String(chosenViCode).toUpperCase();
        currentVotes = parseInt(houseVotes[chosenViCode]) || 0;
    }

    // 3. Fallback to first configuration option in the dropdown list if house data was empty
    if (!chosenViCode && viSel.options.length > 0) {
        chosenViCode = String(viSel.options[0].value).toUpperCase();
        currentVotes = 0;
    }

    // 4. Update the UI DOM attributes directly
    viSel.value = chosenViCode;
    voteBtn.setAttribute('data-count', currentVotes);
    voteBtn.setAttribute('data-max', maxVotes);
    voteBtn.innerText = currentVotes + '/' + maxVotes;
};


async function getVIData(path) {

  let table = document.getElementById("canvass-table");
  let rows = table.querySelectorAll("tbody tr");
  let data = [];

  rows.forEach(row => {
      let electorID = row.cells[1].innerText.trim(); // ENOP
      let ElectorName = row.cells[2].innerText.trim(); // Name
      let vrInput = row.cells[7].querySelector('input');
      let vrValue = vrInput ? vrInput.value.trim() : "";

      let viInput = row.cells[8].querySelector('input');

      let viValue = viInput ? viInput.value.trim() : "";

      let notesInput = row.cells[9].querySelector('input');
      let notesValue = notesInput ? notesInput.value.trim() : "";

      let tagsInput = row.cells[10].querySelector('input');
      let tagsValue = tagsInput ? tagsInput.value.trim() : "";

//        alert( 'Row data:'+electorID+tagsValue);

      console.log(`EID: ${electorID} vr: ${vrValue} vi: ${viValue} notes: ${notesValue} tags: ${tagsValue}`);

      if (electorID && (vrValue || viValue || notesValue || tagsValue)) {
        console.log('Pushing data for: ${electorID}');
          data.push({
              electorID: electorID,
              ElectorName: ElectorName,
              vrResponse: vrValue,
              viResponse: viValue,
              notesResponse: notesValue,
              tagsResponse: tagsValue
          });
      }
  });

  console.log("Collected VI Data:", data);
    // Send data to server

    fetch(path, {  // Use full URL to ensure correct routing
        method: "POST",
         credentials: 'same-origin' ,  // 👈 THIS IS CRITICAL
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ viData: data }),  // Send the necessary data
    })
    .then(response => {
        // Check if the response status is OK (200)
        if (!response.ok) {
            throw new Error("Failed to fetch data: " + response.statusText);
        }
        return response.json();  // Parse the response as JSON
    })
    .then(data => {
        console.log("Success:", data);

        // Check if `file` is present and a valid URL
        if (data && data.file) {
//              alert("Loading: " + data.file);
            window.location.assign(data.file);  // Redirect using the file URL
        } else {
            console.error("Error: 'file' is missing or invalid");
        }

        // Update the log window
        var ul = parent.document.getElementById("logwin");
        if (ul) {
            ul.scrollTop = ul.scrollHeight;
        }
    })
    .catch(error => {
        alert("Error: " + error);
        console.error("Error:", error);
    });
};



function displayMap (url) {
		window.location.href = url;
	};

async function fetchTableData(tableName) {
  const old = pessages.pop();
  const ul = parent.document.getElementById("logwin");
  const li = parent.document.createElement("li");

  const PARTY_COLORS = {
    O: "brown", R: "cyan", C: "blue", S: "red",
    LD: "yellow", G: "limegreen", I: "indigo",
    PC: "darkred", SD: "orange", Z: "lightgray",
    W: "white", X: "darkgray"
  };
   const table = document.getElementById("content-table");
   const tabTitle = document.getElementById("selectedTitle");

   if (!table || !tabTitle) {
       console.error("❌ Required DOM elements not found: #content-table or #selectedTitle");
       return;
   }

   const tabHead = table.querySelector("thead");
   const tabBody = table.querySelector("tbody");

   if (!tabHead || !tabBody) {
       console.error("❌ Table structure invalid: missing <thead> or <tbody>");
       return;
   }

   try {
       const res = await fetch(`/get_table/${tableName}`, { credentials: "same-origin" });
       if (!res.ok) throw new Error(`Server returned ${res.status}`);
       const data = await res.json();

       if (!Array.isArray(data) || data.length < 3) {
           console.error("❌ Invalid data format received:", data);
           return;
       }

       const [columnHeaders, rows, title] = data;
//       tabTitle.textContent = title;
       tabHead.innerHTML = "";
       tabBody.innerHTML = "";

       // --- 1. Filtered Table header ---
       const headRow = document.createElement("tr");
       headRow.innerHTML = `<th>?</th>` +
           columnHeaders
               .filter(h => h.toLowerCase() !== 'nid') // 🎯 Skip NID in header
               .map(h => `<th>${h.toUpperCase()}</th>`)
               .join('');
       tabHead.appendChild(headRow);

       const selectedParty = document.getElementById("yourparty")?.value;

       // --- 2. Filtered Table body ---
       rows.forEach(record => {
           const row = document.createElement("tr");

           // Extract the NID for the checkbox (it exists in 'record' but we won't show it in a cell)
           const nid = record['nid'] || record['id'] || "";

           row.innerHTML = `<td>
               <input type="checkbox"
                      class="selectRow"
                      value="${nid}"
                      data-nid="${nid}">
             </td>` +
             columnHeaders
               .filter(h => h.toLowerCase() !== 'nid') // 🎯 Skip NID in rows
               .map(h => {
                   const value = record[h] ?? "";
                   const color = (selectedParty && h === selectedParty) ? (PARTY_COLORS[selectedParty] || 'inherit') : '';
                   return `<td style="background-color:${color}">${value}</td>`;
               }).join('');

           tabBody.appendChild(row);
       });

       console.log(`✅ TABLE "${tableName}" populated with ${rows.length} rows.`);
   } catch (err) {
       console.error("❌ Error fetching table data:", err);
   }
}




function email_csv(csv, filename) {
  var csvFile;
  var downloadLink;
  csvFile = new Blob([csv], {type: "text/csv"});
  FileLink = document.createElement("a");
  FileLink.download = filename;
  FileLink.href = window.URL.createObjectURL(csvFile);
  document.body.appendChild(FileLink);
  alert("Need to invoke javascript email client"+ FileLink)
};


function openForm() {
    document.getElementById("myForm").style.display = "block";
  };

function closeForm() {
    document.getElementById("myForm").style.display = "none";
  };

function email_html_to_base(html, email) {
  var csv = [];
  var rows = document.querySelectorAll("table tr");
  var row = [], cols = rows[0].querySelectorAll("td, th");
  for (var j = 0; j < cols.length; j++) {
      row.push(cols[j].innerText);
    };
  csv.push(row.join(","));
  for (var i = 1; i < rows.length; i++) {
      var row = [], cols = rows[i].querySelectorAll("td, th");
      for (var j = 0; j < cols.length-1; j++) {
          row.push(cols[j].innerText);
          };
      var selected = cols[6];
      var  slots = selected.querySelectorAll("span input");
        for (var k = 0; k < slots.length; k++) {
            if (slots[k].checked) {
              row.push(slots[k].value)
            };
          };
  csv.push(row.join(","));
  }
  // Download CSV
  email_csv(csv.join("\n"), email);
};

function download_csv(csv, filename) {
  var csvFile;
  var downloadLink;

  // CSV FILE
  csvFile = new Blob([csv], {type: "text/csv"});

  // Download link
  downloadLink = document.createElement("a");

  // File name
  downloadLink.download = filename;

  // We have to create a link to the file
  downloadLink.href = window.URL.createObjectURL(csvFile);

  // Make sure that the link is not displayed
  downloadLink.style.display = "none";

  // Add the link to your DOM
  document.body.appendChild(downloadLink);

  // Lanzamos
  downloadLink.click();
};

function export_table_to_csv(html, filename) {
var csv = [];
var rows = document.querySelectorAll("table tbody tr");
var headcols = ["PD", "ENOP", "ElectorName", "VI", "Notes"];

csv.push(headcols.join(",")); // ✅ Add header row

let seen = new Set(); // ✅ Track unique rows

for (var i = 1; i < rows.length; i++) { // ✅ Start from row 1 (skip header)
    var row = [], cols = rows[i].querySelectorAll("td");

    if (cols.length > 8) { // ✅ Ensure sufficient columns exist
        var pick = [0, 1, 2, 7, 8]; // ✅ Select relevant columns
        for (var j of pick) {
            let cellText = cols[j].innerText.trim().replaceAll(",", "").toUpperCase(); // ✅ Normalize text
            row.push(cellText);
        }

        let rowString = row.join(",").replace(/\s+/g, ""); // ✅ Remove extra spaces

        // ✅ Ensure "VI" or "Notes" is filled properly
        let vi = row[3] ? row[3].trim() : "";
        let notes = row[4] ? row[4].trim() : "";

        if (!seen.has(rowString) && (vi !== "" || notes !== "")) {
            seen.add(rowString); // ✅ Mark row as added
            csv.push(rowString);
        } else {
            console.log(`Skipped duplicate or empty row ${i}:`, rowString);
        }
    }
}

  console.log("CSV Output:\n", csv.join("\n")); // ✅ Debug CSV output
  console.log("CSV Array Inside the Function:", csv);

  if (csv.length > 1) {
      download_csv(csv.join("\n"), filename.split("/").pop());
  } else {
      alert("No data entered to save!");
  }
}

var layerUpdate = function (path) {
  // Send a message to the parent
      var filename = path.split('/').pop().replace("-SDATA.html","-SDATA.csv").replace("-WDATA.html","-WDATA.csv");
      var html = document.querySelector("#canvass-table").outerHTML;
//         export_table_to_csv(html, filename);
//        console.log(filename);
      var htmlpath = path.replace("-SDATA.csv","-PRINT.html").replace("-WDATA.csv","-PRINT.html");
      getVIData(htmlpath);
      window.parent.postMessage({type:"Refreshing summary data set"}, '*');
      };

function inputVI(VI) {
  let x = VI.value.toUpperCase();
  const VIDopt = parent.document.getElementById("yourparty");
  VI.value = x;
  const codes = Array.from(VIDopt.options).map(opt => opt.value.toUpperCase());
//    alert("VI Options:"+codes);
  if (codes.includes(x)) {
//  let y = "<span> <input type=\"text\" onchange=\"copyinput(this)\" maclength=\"2\" size=\"2\" name=\"example-unique-id-A3078.0\" id=\"example-unique-id-E3078.0\" placeholder=\"{0}\"></span>".format(x);
  console.log(`Valid VI code: ${x}`);
    VI.style.color = 'blue';
//    VI.innerHTML = x;
      }
  else {
    VI.style.color = 'grey';
    console.warn(`Invalid VI code: ${x}`);
//    VI.innerHTML = x;
  }
  };

  function inputVR(VR) {
    let x = VR.value.toUpperCase();
    VR.value = x;

    const VIDopt = parent.document.getElementById("yourparty");
    const codes = Array.from(VIDopt.options).map(opt => opt.value.toUpperCase());

    if (codes.includes(x)) {
      // Valid code, do something
      VR.style.color = 'blue';
      console.log(`Valid VR code: ${x}`);
    } else {
      // Invalid code, optionally warn or clear input
      VR.style.color = 'grey';
      console.warn(`Invalid VR code: ${x}`);
    }
  }


  function inputNS(NS) {
    let x = NS.value.toUpperCase();
    NS.style.color = 'blue';
    NS.value = x;

    };

function addTag(event, electorId) {
  if (event.key === "Enter") {
    const input = event.target;
    const raw = input.value.trim();
    if (!raw.includes(':')) return;

    // Split at the first colon
    const [tagPart, ...labelParts] = raw.split(':');
    const tag = tagPart.trim();
    const label = labelParts.join(':').trim();  // Handles extra colons in label

    if (!tag || !label) {
      input.classList.add("tag-error");
      console.error("Invalid format. Use: TAGCODE: Label");
      return;
    }

    fetch("/add_tag", {
      method: "POST",
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enop: electorId,
        tag: tag,
        label: label
      })
    })
    .then(response => response.json())
    .then(data => {
      input.classList.remove("tag-new", "tag-existing", "tag-error");

      if (!data.success) {
        console.error("Tag submission failed:", data.error);
        input.classList.add("tag-error");
        return;
      }

      input.classList.add(data.exists ? "tag-existing" : "tag-new");
    })
    .catch(error => {
      console.error("Request failed:", error);
      input.classList.add("tag-error");
    });
  }
}

function removeTag(electorId, tag) {
  fetch("/remove_tag", {
    method: "POST",
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enop: electorId, tag: tag })
  }).then(() => location.reload());
}

/**
 * Updates the max vote count on the button when the house (unit) selection changes.
 * This prevents assigning 5 votes to a house that only has 1 elector.
 */
function updateMaxVote(selectElement) {
    const row = selectElement.closest('.canvass-row');
    const selectedOption = selectElement.options[selectElement.selectedIndex];
    const maxVotes = selectedOption.getAttribute('data-max') || 1;

    const btn = row.querySelector('.vote-btn');

    // Update the button's internal limit
    btn.setAttribute('data-max', maxVotes);

    // Reset the current count to 0 if the house changes (prevents carry-over errors)
    btn.setAttribute('data-count', '0');
    btn.innerText = `0/${maxVotes}`;

    // Reset the VI selector for the new house (will be overwritten if baked data exists)
    const viSelector = row.querySelector('.vi-selector');
    viSelector.selectedIndex = 0;
}

window.loadHouseData = function(selectElement) {
  const currentData = getBakedData()
    const row = selectElement.closest('.canvass-row');
    if (!row) return;

    // 1. Extract IDs from the row attributes
    const walk = row.getAttribute('data-region');
    const street = row.getAttribute('data-street');
    const house = selectElement.value;

    // 2. Get dropdown/button elements
    const opt = selectElement.options[selectElement.selectedIndex];
    const max = parseInt(opt.getAttribute('data-max')) || 1;
    const btn = row.querySelector('.vote-btn');
    const viSelector = row.querySelector('.vi-selector');

    // 3. Fetch record using the new 3-tier hierarchy: Walk > Street > House
    // Uses optional chaining (?.) for a much cleaner lookup
    const record = currentData[walk]?.[street]?.[house];

    // 4. Update UI State based on whether a record exists
    btn.setAttribute('data-max', max);

    if (record) {
        if (viSelector) viSelector.value = record.vi;
        btn.setAttribute('data-count', record.votes);
        btn.innerText = `${record.votes}/${max}`;
    } else {
        // Default state if no data is baked yet
        if (viSelector) viSelector.selectedIndex = 0;
        btn.setAttribute('data-count', '0');
        btn.innerText = `0/${max}`;
    }

    // 5. Trigger visual updates
    const currentCount = parseInt(btn.getAttribute('data-count')) || 0;

    // Refresh row/button colors
    window.updateRowAppearance(row, currentCount, max);

    // Refresh dropdown styling
    window.refreshDropdownColors(selectElement);

};


window.refreshDropdownColors = function(selectElement) {
    const currentData = getBakedData();
    if (!selectElement) return;
    var row = selectElement.closest('.canvass-row') || selectElement.closest('tr');
    if (!row) return;


    const isUnitSelector = selectElement.classList.contains('unit-selector');
    const isVISelector = selectElement.classList.contains('vi-selector');

    // --- LOGIC A: UNIT SELECTOR (Vote Counts) ---
    if (isUnitSelector) {
        // 1. Get both Walk and Street to find the correct data shelf
        var walk = row.getAttribute('data-region');
        var street = row.getAttribute('data-street');

        Array.from(selectElement.options).forEach(opt => {
            var h = opt.value; // House Number/Name
            var m = parseInt(opt.getAttribute('data-max')) || 1;

            // 2. Deep look-up: Walk -> Street -> House
            var rec = (currentData[walk] &&
                       currentData[walk][street] &&
                       currentData[walk][street][h])
                       ? currentData[walk][street][h]
                       : null;

            var v = rec ? parseInt(rec.votes) : 0;

            // 3. UI Indicators (Checkmarks and Dots)
            if (v >= m && m > 0) {
                opt.text = h + " ✅";
                opt.style.color = "#28a745"; // Green
            } else if (v > 0) {
                opt.text = h + " 🟡";
                opt.style.color = "#ffcc00"; // Yellow
            } else {
                opt.text = h;
                opt.style.color = "";
            }
        });

        // Color the main face of the dropdown based on the currently selected house
        const btn = row.querySelector('.vote-btn');
        const cv = parseInt(btn.getAttribute('data-count')) || 0;
        const cm = parseInt(btn.getAttribute('data-max')) || 1;
        selectElement.style.backgroundColor = (cv >= cm && cm > 0) ? "#28a745" : (cv > 0 ? "#ffcc00" : "");
        selectElement.style.color = (cv >= cm && cm > 0) ? "white" : (cv > 0 ? "black" : "");
    }

    // --- LOGIC B: VI SELECTOR (Unchanged, as it doesn't rely on BAKED_DATA) ---
    if (isVISelector) {
        const val = selectElement.value;
        const colors = {
            'R': '#00aaff', // Example: Reform Blue
            'C': '#0087dc', // Conservative Blue
            'S': '#dc3545', // Labour Red
            'LD': '#faa61a', // Lib Dem Orange
            'G': '#6ab023'  // Green
        };
        // Note: I updated these keys to match your VI codes (R, C, S) instead of 1, 2, 3
        selectElement.style.backgroundColor = colors[val] || '#e6f2ff';
        selectElement.style.color = (val === 'R' || val === 'C' || val === 'S') ? 'white' : 'black';
    }
};

window.updateVI = function(selectElement) {
    var parentWindow = window.parent || window;
    var row = selectElement.closest('.canvass-row') || selectElement.closest('tr');
    if (!row) return;

    var unitSel = row.querySelector('.unit-selector');
    var voteBtn = row.querySelector('.vote-btn');
    if (!unitSel || !voteBtn) return;

    // 1. Gather all required identifiers from the active layout state
    var regionId = row.getAttribute('data-region');
    var streetName = row.getAttribute('data-street');
    var uiScope = row.getAttribute('data-scope') || 'walk';
    var selectedHouse = unitSel.value;

    // 2. 🔍 DETERMINISTIC VOTE COUNT CALCULATION
    var finalVotes = null; // Start unassigned to catch true absence

    // Layer A: Check if parent window memory ledger has an unsynced, newer interaction
    var eventLog = parentWindow.BAKED_DATA || [];
    var recentLogEntry = null;

    // Loop backwards to grab the absolute newest entry matching this specific house unit
    for (var i = eventLog.length - 1; i >= 0; i--) {
        var entry = eventLog[i];
        if (entry.region === regionId &&
            entry.street === streetName &&
            entry.house === selectedHouse) {
            recentLogEntry = entry;
            break;
        }
    }

    if (recentLogEntry && recentLogEntry.votes !== undefined) {
        // High priority: use the value they modified live in this session
        finalVotes = parseInt(recentLogEntry.votes);
        if (isNaN(finalVotes)) finalVotes = 0;
        console.log(`💡 Found unsynced live memory value for ${selectedHouse}: ${finalVotes}`);
    } else {
        // Layer B: Fall back to check the server's embedded initial default string attribute
        var rawDefault = row.getAttribute('data-initial-count') || voteBtn.getAttribute('data-initial-count');

        // Strict check: if it's missing, null, or an empty string (""), treat it as ABSENT
        if (rawDefault !== null && rawDefault !== undefined && rawDefault.trim() !== "") {
            finalVotes = parseInt(rawDefault);
            if (isNaN(finalVotes)) finalVotes = 0;
            console.log(`💡 Falling back to server database default string: ${finalVotes}`);
        } else {
            finalVotes = null; // Formally flags that no selection history exists on the server
            console.log(`💡 Server default is ABSENT or empty string. Proceeding to final fallback.`);
        }
    }

    // Layer C: Final Fallback Resolution
    // 🌟 REVISED: If both layers yielded no data, use 0 as your visual/interaction baseline
    if (finalVotes === null) {
        finalVotes = 0;
        console.log(`💡 No memory or server attribute available. Defaulting fallback to 0`);
    }

    // 3. Update UI states to visually display this synchronized calculation
    var maxVotes = parseInt(voteBtn.getAttribute('data-max')) || 1;
    voteBtn.setAttribute('data-count', finalVotes);
    voteBtn.innerText = finalVotes + '/' + maxVotes;

    // 4. FLAT LOG GENERATION LAYER
    if (!parentWindow.BAKED_DATA) parentWindow.BAKED_DATA = [];

    // Append our dropdown modification state with the calculated vote number
    parentWindow.BAKED_DATA.push({
        type: 'vi',
        uiScope: uiScope,
        region: regionId,
        street: streetName,
        house: selectedHouse,
        vi: selectElement.value,
        votes: finalVotes,       // Logged using our layered verification logic
        timestamp: Date.now(),
        synced: false
    });

    // 5. Run standard file synchronization & downstream layout redraw cycles
    if (typeof parentWindow.saveBakedData === 'function') {
        parentWindow.saveBakedData(parentWindow.BAKED_DATA);
    }

    if (typeof window.refreshDropdownColors === 'function') {
        window.refreshDropdownColors(selectElement);
    }

    if (window.updateMarkerStatus) {
        window.updateMarkerStatus(streetName);
    }

    var deployBtn = document.getElementById('deploy-btn');
    if (deployBtn) deployBtn.disabled = false;
};

window.createLozengeElement = function createLozengeElement(loz, { selectable = false, removable = false } = {}) {
 const div = document.createElement("div");
 div.setAttribute("data-type", loz.type);
 div.setAttribute("data-code", loz.code);
 div.setAttribute("draggable", true);
 div.setAttribute("tabindex", "0");  // ✅ Makes the lozenge focusable
 div.setAttribute("id", `lozenge-${loz.type}-${loz.code}-${Math.random().toString(36).substring(2, 8)}`);
 div.textContent = loz.code;

 div.className = `lozenge ${loz.type}-lozenge`;
 if (!selectable) div.classList.add("dropped");
 div.textContent = loz.code;

 div.addEventListener("dragstart", (e) => {
   const payload = {
     type: loz.type,
     code: loz.code
   };

   // Always send JSON (the drop handler expects "application/json")
   e.dataTransfer.setData("application/json", JSON.stringify(payload));

   // Optional: visually highlight
   e.dataTransfer.effectAllowed = "copy";
   div.classList.add("dragging");
 });



 // Decide tooltip content for tippy
 let tooltipContent = null;

 if (loz.type === "area") {
   const areaInfo = window.areas?.[loz.code];
   tooltipContent = areaInfo?.tooltip_html || loz.info || null;
 } else if (loz.type === "resource") {
   const resourceInfo = window.resources?.[loz.code];
   tooltipContent = resourceInfo?.Firstname; + " " + resourceInfo?.Surname;
   console.log("Resource Tooltips",tooltipContent);
 } else if (loz.type === "place") {
       const placeInfo = window.places?.[loz.code];
       tooltipContent = placeInfo?.tooltip;
       console.log("Place Tooltip ",loz.code,placeInfo);
       console.log("placeDetails keys:", Object.keys(window.places));
       console.log("placeDetails values:", window.places);
 } else if (loz.type === "tag") {
       const tagInfo = window.task_tags?.[loz.code];
       tooltipContent = tagInfo;
       console.log("Task tag Tooltip ",loz.code,tagInfo);
       console.log("tagDetails values:", Object.values(window.task_tags));

     };


 if (tooltipContent) {
   tippy(div, {
     content: tooltipContent,
     hideOnClick: true,
     allowHTML: true,
     trigger: 'click',
     interactive: true,
     theme: 'light', // optional
     appendTo: document.body,
   });
 }
 div.removeAttribute("title");
 div.removeAttribute("data-info"); // if you're using this anywhere


 // Tooltip setup (as before)...

 // ✅ Highlight (for palette lozenges)
 if (selectable) {
   div.addEventListener("click", () => {
     highlightLozenge(div);
   });
 }

 // ❌ Removal (for dropped lozenges)
 if (removable) {
   div.addEventListener("click", () => {
     div.remove();
   });
 }

 return div;
}
