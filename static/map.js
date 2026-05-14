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
  ul.appendChild(li);
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

window.BAKED_DATA = window.BAKED_DATA ||
                    (parent && parent.BAKED_DATA) || {
    walk: {},
    pd: {},
    ward: {},
    elector: {}
};

/* --- Top of map.js --- */
/* --- Top of map.js --- */
// 1. Map Handle
var fmap;

// This acts as your "Fast Lookup" dictionary
window.mapLayerIndex = {};

// 2. Data Handle: Use local data if it exists, otherwise reach out to the parent
var getBakedData = function() {
    return window.BAKED_DATA || (parent && parent.BAKED_DATA) || {};
};

// --- Add this to your JS file ---
const addMapLogo = (map) => {
    const logoControl = L.control({ position: 'bottomleft' });

    logoControl.onAdd = function() {
        // Create the outer container defined in your CSS
        const div = L.DomUtil.create('div', 'leaflet-logo-container');

        // Create the inner icon div that uses the mask
        const icon = L.DomUtil.create('div', 'leaflet-logo-icon', div);

        return div;
    };

    logoControl.addTo(map);
};

/**
 * Saves the global data object to browser storage.
 * @param {Object} data - The current BAKED_DATA object.
 */
window.saveBakedData = function(data) {
    try {
        // 1. Safety check: Don't save if data is empty or invalid
        if (!data || typeof data !== 'object') return;

        // 2. Convert the Object to a String (JSON)
        const dataString = JSON.stringify(data);

        // 3. Save to localStorage under a unique key
        localStorage.setItem('CANVASS_BAKED_DATA', dataString);

        // 4. Update the global variable to ensure all functions see the same data
        window.BAKED_DATA = data;

        console.log("💾 Progress saved to LocalStorage");
    } catch (e) {
        console.error("❌ Failed to save to LocalStorage:", e);

        // Handle QuotaExceededError (if storage is full)
        if (e.code === 22 || e.code === 1014) {
            alert("Local storage is full. Progress might not be saved.");
        }
    }
};

/**
 * Loads the data back from storage on page load.
 */
window.getBakedData = function() {
    try {
        // 1. Try to find existing data in storage
        const saved = localStorage.getItem('CANVASS_BAKED_DATA');

        if (saved) {
            // 2. Parse the string back into a JS Object
            window.BAKED_DATA = JSON.parse(saved);
            return window.BAKED_DATA;
        }
    } catch (e) {
        console.error("❌ Error loading saved data:", e);
    }

    // 3. Fallback: Return empty object if nothing found
    window.BAKED_DATA = window.BAKED_DATA || {};
    return window.BAKED_DATA;
};


// This self-invoking function starts looking for the map immediately
(function startMapCatcher() {
  /* --- Inside your startMapCatcher in map.js --- */
  const findMap = () => {
      // 1. Check current window
      for (const key in window) {
          // Use 'window.L' to ensure it exists here
          if (key.startsWith('map_') && window.L && window[key] instanceof window.L.Map) {
              fmap = window[key];
              window.fmap = fmap;
              // ... inside your findMap function ...

              if (key.startsWith('map_') && window.L && window[key] instanceof window.L.Map) {
                  fmap = window[key];
                  window.fmap = fmap;

                  // --- ADD THE POPUP LISTENER HERE ---
                  fmap.on('popupopen', function(e) {
                      const container = e.popup._contentNode;
                      const firstRow = container.querySelector('.canvass-row');

                      if (firstRow) {
                          const region_id = firstRow.getAttribute('data-region');

                          if (window.plotL1Progress) {
                            // 1. Pull keys dynamically from your global config
                            const tagsToUpdate = Object.keys(window.task_tags || {});

                            // 2. Refresh every ghost layer for this specific walk
                            // The prefix guard inside the function will handle skipping M-tags automatically
                            tagsToUpdate.forEach(tagCode => {
                                window.plotL1Progress(region_id, tagCode,'walk');
                            });

                              console.log(`✨ Popup Sync: All ghost layers refreshed for Walk ${region_id}`);
                          }
                      }
                  });
                  // Inside your findMap() success block:
                  fmap.invalidateSize();
                  const currentData = getBakedData()
                  const tagRegistry = window.TAG_TO_GROUP_MAPPING || {};
                  const tagCodes = Object.keys(tagRegistry);

                  if (currentData) {
                      console.log("🎯 Map found! Initializing all region visuals for all tags...");
                      addMapLogo(fmap);

                      // Iterate through every Walk/Region in your data
                      Object.keys(currentData).forEach(region_id => {

                          // Check if we have multiple tags to initialize
                          if (tagCodes.length > 0) {
                              tagCodes.forEach(code => {
                                  window.plotL1Progress(region_id, code,'walk');
                              });
                          } else {
                              // Fallback to L1 if no registry found
                              window.plotL1Progress(region_id, 'L1','walk');
                          }
                      });
                  }
                  return true;
              }

              return true;
          }
      }

      // 2. Target iframe1 specifically
      const frame = document.getElementById('iframe1');
      if (frame && frame.contentWindow) {
          const frameWin = frame.contentWindow;
          // Look for the map using the IFRAME'S version of Leaflet (frameWin.L)
          for (const key in frameWin) {
              if (key.startsWith('map_') && frameWin.L && frameWin[key] instanceof frameWin.L.Map) {
                  fmap = frameWin[key];
                  window.fmap = fmap;
                  // ... repeat the same for the iframe success block ...
                  if (key.startsWith('map_') && frameWin.L && frameWin[key] instanceof frameWin.L.Map) {
                      fmap = frameWin[key];
                      window.fmap = fmap;

                      // --- AND HERE ---
                      fmap.on('popupopen', function(e) {
                          // ... same logic as above ...
                      });

                      console.log("🎯 map.js: Found Folium map inside iframe1:", key);
                      return true;
                  }
                  console.log("🎯 map.js: Found Folium map inside iframe1:", key);
                  return true;
              }
          }
      }
      return false;
  };

    // If not found, check every 100ms
    if (!findMap()) {
        const interval = setInterval(() => {
            if (findMap()) clearInterval(interval);
        }, 100);

        // Safety: Stop looking after 10 seconds if no map is found
        setTimeout(() => clearInterval(interval), 10000);
    }
    /* Add this to the end of your startMapCatcher function */
if (window.parent && window.parent !== window) {
    // If I am the iframe, I'll tell my parent I have a map
    for (const key in window) {
        if (key.startsWith('map_') && window[key] instanceof L.Map) {
            window.parent.fmap = window[key];
            console.log("📢 Iframe pushed map to Parent");
        }
    }
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

window.updateElectorTag = function(walk, street, unit, code, isActive, uiScope = 'walk') {

    const currentData = getBakedData() || {};
    if (!currentData) return;

    // -----------------------------
    // ENSURE STRUCTURE
    // -----------------------------
    if (!currentData[uiScope]) currentData[uiScope] = {};
    if (!currentData[uiScope][walk]) currentData[uiScope][walk] = {};
    if (!currentData[uiScope][walk][street]) {
        currentData[uiScope][walk][street] = {
            street_weight: 0,
            ts: Date.now()
        };
    }

    const streetObj = currentData[uiScope][walk][street];

    if (!streetObj[unit]) {
        streetObj[unit] = {
            vi: "",
            votes: "0",
            tags: {},
            ts: Date.now()
        };
    }

    const house = streetObj[unit];

    if (!house.tags) house.tags = {};

    // -----------------------------
    // TAG MUTATION (OBJECT-BASED)
    // -----------------------------
    if (isActive) {
        house.tags[code] = "y";
    } else {
        house.tags[code] = "n";
    }

    house.ts = Date.now();
    streetObj.ts = Date.now();

    // -----------------------------
    // PERSIST
    // -----------------------------
    window.BAKED_DATA = currentData;

    if (typeof saveBakedData === 'function') {
        saveBakedData(currentData);
    }

    console.log(`✅ Updated ${walk}/${street}/${unit} tag ${code} = ${house.tags[code]}`);
};

window.updateTagToggles = function(selector, uiScope = 'walk') {

    const row = selector.closest('.canvass-row') || selector.closest('tr');
    if (!row) return;

    const region = row.getAttribute('data-region');
    const street = row.getAttribute('data-street');
    const house = selector.value;

    const currentData = getBakedData() || {};

    // -----------------------------
    // SAFE NAVIGATION (HOUSE-LEVEL ONLY)
    // -----------------------------
    const houseData =
        currentData[uiScope] &&
        currentData[uiScope][region] &&
        currentData[uiScope][region][street] &&
        currentData[uiScope][region][street][house]
            ? currentData[uiScope][region][street][house]
            : null;

    const tags = (houseData && houseData.tags) ? houseData.tags : {};

    // -----------------------------
    // UPDATE UI
    // -----------------------------
    row.querySelectorAll('.tag-toggle').forEach(span => {

        const code = span.getAttribute('data-code');
        const val = tags[code] || 'n';

        if (val === 'y') {
            span.classList.remove('tag-inactive');
            span.classList.add('tag-active');
            span.innerText = 'y';
        } else {
            span.classList.remove('tag-active');
            span.classList.add('tag-inactive');
            span.innerText = 'n';
        }
    });
};

window.handleTagClick = function(span, uiScope = 'walk') {

    const isInactive = span.classList.contains('tag-inactive');
    const newValue = isInactive ? 'y' : 'n';
    const code = span.getAttribute('data-code');

    const currentData =
        (typeof getBakedData === 'function')
            ? getBakedData()
            : (window.BAKED_DATA || {});

    // -----------------------------
    // UI TOGGLE
    // -----------------------------
    if (isInactive) {
        span.classList.remove('tag-inactive');
        span.classList.add('tag-active');
        span.innerText = 'y';
    } else {
        span.classList.remove('tag-active');
        span.classList.add('tag-inactive');
        span.innerText = 'n';
    }

    // -----------------------------
    // CONTEXT
    // -----------------------------
    const row = span.closest('.canvass-row') || span.closest('tr');
    if (!row) return;

    const region = row.getAttribute('data-region');
    const street = row.getAttribute('data-street');
    const house = row.querySelector('.unit-selector')?.value;

    if (!region || !street || !house) return;

    // -----------------------------
    // ENSURE STRUCTURE (HOUSE-FIRST MODEL)
    // -----------------------------
    if (!currentData[uiScope]) currentData[uiScope] = {};
    if (!currentData[uiScope][region]) currentData[uiScope][region] = {};
    if (!currentData[uiScope][region][street]) {
        currentData[uiScope][region][street] = {
            street_weight: 0,
            ts: Date.now()
        };
    }

    const streetObj = currentData[uiScope][region][street];

    if (!streetObj[house]) {
        streetObj[house] = {
            vi: "",
            votes: "0",
            tags: {},
            ts: Date.now()
        };
    }

    const houseObj = streetObj[house];

    if (!houseObj.tags) houseObj.tags = {};

    // -----------------------------
    // MUTATION LOGIC (HOUSE-LEVEL ONLY)
    // -----------------------------

    if (newValue === 'y') {
        houseObj.tags[code] = 'y';
    } else {
        houseObj.tags[code] = 'n';
    }

    houseObj.ts = Date.now();
    streetObj.ts = Date.now();

    // -----------------------------
    // PERSIST
    // -----------------------------
    window.BAKED_DATA = currentData;

    if (typeof saveBakedData === 'function') {
        saveBakedData(currentData);
    }

    // -----------------------------
    // VISUAL UPDATE
    // -----------------------------

    if (window.plotL1Progress) {
        window.plotL1Progress(region, code, uiScope);
    } else if (parent.plotL1Progress) {
        parent.plotL1Progress(region, code, uiScope);
    }
};

window.updateMarkerStatus = function(region_id, uiScope = 'walk') {

    if (!region_id) return;

    const currentData = getBakedData() || {};
    const scopeData = currentData[uiScope] || {};
    const regionData = scopeData[region_id];

    if (!regionData) return;

    // -----------------------------
    // 1. COUNT COMPLETED UNITS
    // (ONLY HOUSE LEVEL DATA)
    // -----------------------------
    let completedUnits = 0;

    Object.values(regionData).forEach(street => {

        if (!street || typeof street !== 'object') return;

        Object.values(street).forEach(house => {

            // skip metadata nodes
            if (!house || typeof house !== 'object') return;
            if (!house.tags) return;

            if (parseInt(house.votes || "0") > 0) {
                completedUnits++;
            }
        });
    });

    // -----------------------------
    // 2. GET EXPECTED HOUSE COUNT (FROM MAP)
    // -----------------------------
    let expectedHouses = 0;

    const activeMap =
        window.fmap ||
        parent.fmap ||
        (document.getElementById('iframe1')?.contentWindow?.fmap);

    if (!activeMap) {
        console.warn("fmap not found. Is iframe1 loaded yet?");
        return;
    }

    activeMap.eachLayer(layer => {
        const props = layer.feature?.properties;
        if (props?.region_id === region_id) {
            expectedHouses = props.expected_houses || 0;
        }
    });

    // -----------------------------
    // 3. COLOR LOGIC
    // -----------------------------
    const healthColor =
        (expectedHouses > 0 && completedUnits >= expectedHouses)
            ? "#28a745"
            : (completedUnits > 0 ? "#ffcc00" : null);

    // -----------------------------
    // 4. UPDATE LABEL
    // -----------------------------
    const labelSpan = document.getElementById(`label-${region_id}`);

    if (labelSpan) {
        if (healthColor) {
            labelSpan.style.background = healthColor;
            labelSpan.style.color = "white";
        }
    }

    // -----------------------------
    // 5. UPDATE POLYGON STYLE
    // -----------------------------
    activeMap.eachLayer(layer => {

        const props = layer.feature?.properties;

        if (props?.region_id === region_id) {

            if (healthColor) {
                layer.setStyle({
                    fillColor: healthColor,
                    fillOpacity: 0.8
                });
            }
        }
    });
};

// map.js

window.walkLayersDeep = function(layer, callback) {
    if (!layer) return;

    // Execute callback.
    // If the callback returns 'true', we stop recursing (Short-circuit)
    const stop = callback(layer);
    if (stop === true) return true;

    if (typeof layer.eachLayer === 'function') {
        let found = false;
        layer.eachLayer(child => {
            if (found) return; // Skip remaining siblings
            if (window.walkLayersDeep(child, callback)) {
                found = true;
            }
        });
        return found;
    }
    return false;
};

window.plotL1Progress = function(
    region_id,
    targetTag = 'L1',
    uiScope = 'walk'
) {

    console.group(`🏗️ BUCKET-FIRST UPDATE: ${region_id} [${targetTag}]`);

    const activeMap = window.fmap || parent.fmap;
    const Leaflet = window.L || parent.L;
    const cleanId = String(region_id).trim();

    // -------------------------------------------------
    // 1️⃣ LOAD DATA
    // -------------------------------------------------

    const allData =
        typeof getBakedData === 'function'
            ? getBakedData()
            : (window.BAKED_DATA || {});

    const fullData = allData[uiScope] || {};
    const regionData = fullData[cleanId];

    if (!regionData) {
        console.warn(`⚠️ No data found for ${uiScope}:${cleanId}`);
        console.groupEnd();
        return;
    }

    // -------------------------------------------------
    // 2️⃣ CALCULATE COMPLETION
    // -------------------------------------------------

    let completedWeight = 0;
    let totalPossible = regionData.region_total_houses || 0;

    // Fallback denominator from map geometry
    if (totalPossible === 0) {
      walkLayersDeep(activeMap, l => {
            if (
                l.feature?.properties?.region_id === cleanId &&
                !l.is_ghost
            ) {
                totalPossible = parseInt(
                    l.feature.properties.expected_houses || 0
                );
            }
        });
    }

    Object.values(regionData).forEach(street => {

        if (
            street?.street_weight &&
            Object.values(street).some(
                u => u?.tags?.[targetTag] === 'y'
            )
        ) {
            completedWeight += street.street_weight;
        }
    });

    const finalOpacity =
        totalPossible > 0
            ? (0.8 * (completedWeight / totalPossible))
            : 0;

    // -------------------------------------------------
    // 3️⃣ FIND TARGET BUCKET FIRST
    // -------------------------------------------------

    const findBucket = () => {

        const iframe = document.getElementById('iframe1');
        const mapWin = iframe ? iframe.contentWindow : window;

        for (const key in mapWin) {

            if (key.startsWith("layer_control_")) {

                const layers =
                    mapWin[key].overlays ||
                    mapWin[key]._layers;

                for (const name in layers) {

                    if (name.includes(`[${targetTag}]`)) {
                        return layers[name].layer || layers[name];
                    }
                }
            }
        }

        return null;
    };

    const targetGroup = findBucket();

    if (!targetGroup) {
        console.error("❌ Target Bucket not found.");
        console.groupEnd();
        return;
    }

    // -------------------------------------------------
    // 4️⃣ FIND EXISTING GHOST FIRST
    // -------------------------------------------------
    console.log("DEBUG OPACITY", { region, targetTag, completedWeight, totalPossible, finalOpacity });
    const ghostUniqueId = `ghost_${targetTag}_${cleanId}`;

    let existingGhost = null;

    targetGroup.eachLayer(l => {

        if (l.ghost_id === ghostUniqueId) {
            existingGhost = l;
        }
    });

    // -------------------------------------------------
    // 5️⃣ FAST PATH: UPDATE EXISTING GHOST
    // -------------------------------------------------

    if (existingGhost) {

        console.log(`♻️ Updating existing ghost: ${ghostUniqueId}`);

        existingGhost.setStyle({
            fillOpacity: finalOpacity
        });

        // Respect overlay toggle state
        if (!activeMap.hasLayer(targetGroup)) {

            activeMap.removeLayer(existingGhost);

        } else if (!activeMap.hasLayer(existingGhost)) {

            existingGhost.addTo(activeMap);
        }

        console.groupEnd();
        return;
    }

    // -------------------------------------------------
    // 6️⃣ ONLY NOW SEARCH FOR BLUEPRINT
    // -------------------------------------------------

    let blueprintGeometry = null;
    let foundButGhost = false;
    const allSeenIds = [];

    walkLayersDeep(activeMap, l => {

        if (l.feature?.properties) {

            const idOnMap = String(
                l.feature.properties.region_id
            ).trim();

            allSeenIds.push(idOnMap);

            if (idOnMap === cleanId) {

                if (l.is_ghost) {

                    foundButGhost = true;

                } else {

                    blueprintGeometry = l.feature.geometry;
                }
            }
        }
    });

    // -------------------------------------------------
    // 7️⃣ FAIL IF NO BLUEPRINT EXISTS
    // -------------------------------------------------

    if (!blueprintGeometry) {

        console.error(`❌ MAPPING FAIL for ID: "${cleanId}"`);

        console.log(`- Found as Ghost? ${foundButGhost}`);

        console.log(
            `- Available IDs on map:`,
            [...new Set(allSeenIds)]
        );

        const caseMatch = allSeenIds.find(
            id => id.toLowerCase() === cleanId.toLowerCase()
        );

        if (caseMatch) {

            console.warn(
                `- 💡 Hint: Found case-insensitive match: "${caseMatch}".`
            );
        }

        console.warn(
            "⚠️ Source polygon not found for blueprint."
        );

        console.groupEnd();
        return;
    }

    // -------------------------------------------------
    // 8️⃣ MANUFACTURE NEW GHOST
    // -------------------------------------------------

    console.log(
        `✨ Manufacturing new independent poly for ${ghostUniqueId}`
    );

    const newPoly = Leaflet.geoJSON(
        blueprintGeometry,
        {
            pane: 'overlayPane',

            style: {
                color: "transparent",
                fillColor:
                    targetTag.startsWith('L')
                        ? "#333"
                        : "#800080",

                fillOpacity: finalOpacity,
                interactive: false
            }
        }
    );

    newPoly.is_ghost = true;
    newPoly.ghost_id = ghostUniqueId;

    targetGroup.addLayer(newPoly);

    // Respect layer toggle state
    if (!activeMap.hasLayer(targetGroup)) {

        activeMap.removeLayer(newPoly);
    }

    console.groupEnd();
};

window.incrementVoteCount = function(btn, uiScope = 'walk') {

    console.log("➕ incrementVoteCount clicked");

    const count =
        ((parseInt(btn.getAttribute('data-count')) || 0) + 1) %
        ((parseInt(btn.getAttribute('data-max')) || 1) + 1);

    const max = parseInt(btn.getAttribute('data-max')) || 1;

    btn.setAttribute('data-count', count);
    btn.innerText = `${count}/${max}`;

    const currentData = getBakedData() || {};

    const row = btn.closest('.canvass-row');
    if (!row) return;

    const walk = row.getAttribute('data-region');
    const street = row.getAttribute('data-street');

    const house = row.querySelector('.unit-selector')?.value;
    const vi = row.querySelector('.vi-selector')?.value || "";

    if (!walk || !street || !house) return;

    // -------------------------
    // ENSURE STRUCTURE
    // -------------------------
    currentData[uiScope] ??= {};
    currentData[uiScope][walk] ??= {};
    currentData[uiScope][walk][street] ??= {};
    currentData[uiScope][walk][street][house] ??= {
        vi: "",
        votes: "0",
        tags: {},
        ts: Date.now()
    };

    const houseObj = currentData[uiScope][walk][street][house];

    // preserve tags no matter what
    houseObj.tags ??= {};

    // -------------------------
    // UPDATE HOUSE FACTS
    // -------------------------
    houseObj.vi = vi;
    houseObj.votes = String(count);
    houseObj.ts = Date.now();

    console.log(
        `💾 Saved: [${uiScope}] ${walk}/${street}/${house} = ${count} votes`
    );

    // -------------------------
    // UI updates
    // -------------------------
    window.refreshDropdownColors?.(row.querySelector('.unit-selector'));
    window.updateRowAppearance?.(row, count, max);

    // -------------------------
    // MAP UPDATE (street-level aggregation trigger)
    // -------------------------
    window.updateMarkerStatus?.(walk);
};

window.handleTagClick = function(span, uiScope = 'walk') {

    const isInactive = span.classList.contains('tag-inactive');
    const code = span.getAttribute('data-code');
    const newValue = isInactive ? 'y' : 'n';

    const currentData = getBakedData() || {};

    const row = span.closest('.canvass-row') || span.closest('tr');
    if (!row) return;

    const walk = row.getAttribute('data-region');
    const street = row.getAttribute('data-street');
    const house = row.querySelector('.unit-selector')?.value;

    if (!walk || !street || !house) return;

    // -------------------------
    // ENSURE STRUCTURE
    // -------------------------
    currentData[uiScope] ??= {};
    currentData[uiScope][walk] ??= {};
    currentData[uiScope][walk][street] ??= {};
    currentData[uiScope][walk][street][house] ??= {
        vi: "",
        votes: "0",
        tags: {},
        ts: Date.now()
    };

    const houseObj = currentData[uiScope][walk][street][house];
    houseObj.tags ??= {};

    // -------------------------
    // TOGGLE TAG
    // -------------------------
    houseObj.tags[code] = newValue;

    houseObj.ts = Date.now();

    // -------------------------
    // UI UPDATE
    // -------------------------
    span.classList.toggle('tag-active', newValue === 'y');
    span.classList.toggle('tag-inactive', newValue === 'n');
    span.innerText = newValue;

    window.BAKED_DATA = currentData;

    saveBakedData?.(currentData);

    window.plotL1Progress?.(walk, code, uiScope);
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

    // Update the specific Walk (Region) on the map
    window.updateMarkerStatus(walk);
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
  currentData = getBakedData()
    var row = selectElement.closest('.canvass-row') || selectElement.closest('tr');

    // 1. Grab all three identifiers (Walk, Street, House)
    var walk = row.getAttribute('data-region');
    var street = row.getAttribute('data-street');
    var house = row.querySelector('.unit-selector').value;

    // 2. Ensure the 3-tier hierarchy exists
    if (!currentData[walk]) currentData[walk] = {};
    if (!currentData[walk][street]) currentData[walk][street] = {};

    // 3. Ensure house record exists without wiping out existing votes or tags
    if (!currentData[walk][street][house]) {
        currentData[walk][street][house] = { votes: "0", tags: {} };
    }

    // 4. Update only the VI and timestamp
    currentData[walk][street][house].vi = selectElement.value;
    currentData[walk][street][house].ts = Date.now();

    // 5. Re-color the dropdown UI immediately
    window.refreshDropdownColors(selectElement);

    // 6. Trigger the Map Marker/Polygon refresh
    // (Still passing 'street' assuming your map uses street-level markers)
    if (window.updateMarkerStatus) {
        window.updateMarkerStatus(street);
    }

    console.log(`📝 Saved Intent for [${walk}] ${street} ${house}: ${selectElement.value}`);
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
