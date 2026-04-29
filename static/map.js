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

window.BAKED_DATA = window.BAKED_DATA || (parent && parent.BAKED_DATA) || {};

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
                          const region_id = firstRow.getAttribute('data-walk');

                          if (window.updateWalkVisuals) {
                              // 1. Get all tag codes that actually exist in your data
                              // Or use: Object.keys(window.TAG_TO_GROUP_MAPPING)
                              const tagsToUpdate = ['L1', 'L2', 'L3', 'M1', 'M2', 'M3'];

                              // 2. Refresh every ghost layer for this specific walk
                              tagsToUpdate.forEach(tagCode => {
                                  window.updateWalkVisuals(region_id, tagCode);
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
                                  window.updateWalkVisuals(region_id, code);
                              });
                          } else {
                              // Fallback to L1 if no registry found
                              window.updateWalkVisuals(region_id, 'L1');
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

window.updateElectorTag = function(walk, street, unit, code, isActive) {
    // 1. Get the data source (check parent if local is empty)
    const currentData = getBakedData()

    if (!currentData) return;

    // 2. Ensure the Walk > Street > Unit path exists
    if (!currentData[walk]) currentData[walk] = {};
    if (!currentData[walk][street]) currentData[walk][street] = {};
    if (!currentData[walk][street][unit]) {
        currentData[walk][street][unit] = {
            vi: "U",
            votes: "0",
            tags: "",
            ts: Date.now()
        };
    }

    // 3. Process the tags
    let currentTags = currentData[walk][street][unit].tags || "";
    let tagList = currentTags.split(',').filter(t => t.trim() !== "");

    if (isActive) {
        if (!tagList.includes(code)) tagList.push(code);
    } else {
        tagList = tagList.filter(t => t !== code);
    }

    // 4. Save back and log
    currentData[walk][street][unit].tags = tagList.join(',');
    currentData[walk][street][unit].ts = Date.now(); // Update timestamp

    console.log(`✅ Updated ${walk} > ${street} [${unit}] tags: ${currentData[walk][street][unit].tags}`);
};

window.updateTagToggles = function(selector) {
    var row = selector.closest('.canvass-row') || selector.closest('tr');
    var walk = row.getAttribute('data-walk'); // Grab the Walk ID from the HTML
    var street = row.getAttribute('data-street');
    var house = selector.value;
    currentData = getBakedData()

    // Navigate the 3-tier hierarchy: Walk -> Street -> House
    var houseData = (currentData[walk] &&
                     currentData[walk][street] &&
                     currentData[walk][street][house])
                     ? currentData[walk][street][house]
                     : null;

    var tags = (houseData && houseData.tags) ? houseData.tags : {};

    row.querySelectorAll('.tag-toggle').forEach(span => {
        var code = span.getAttribute('data-code');
        // Since tags is an object, we check the specific code (e.g., tags['L1'])
        var val = tags[code] || 'n';

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

window.handleTagClick = function(span) {
    // 1. Get the current state
    var isInactive = span.classList.contains('tag-inactive');
    var newValue = isInactive ? 'y' : 'n';
    var code = span.getAttribute('data-code');

    // FETCH: Get the live data object
    var currentData = (typeof getBakedData === 'function') ? getBakedData() : (window.BAKED_DATA || {});

    // 2. Visual Toggle
    if (isInactive) {
        span.classList.remove('tag-inactive');
        span.classList.add('tag-active');
        span.innerText = 'y';
    } else {
        span.classList.remove('tag-active');
        span.classList.add('tag-inactive');
        span.innerText = 'n';
    }

    // 3. Data Extraction
    var row = span.closest('.canvass-row') || span.closest('tr');
    var walk = row.getAttribute('data-walk');
    var street = row.getAttribute('data-street');
    var house = row.querySelector('.unit-selector').value;
    var streetWeight = parseInt(row.cells[1].innerText) || 0;

    // 4. Ensure Hierarchy & Preserve Total Houses
    if (!currentData[walk]) {
        // Try to find the walk total in the UI to bake it in permanently
        var totalEl = document.querySelector('.walk-total-display');
        currentData[walk] = {
            region_total_houses: totalEl ? parseInt(totalEl.innerText) : 0
        };
    }

    if (!currentData[walk][street]) currentData[walk][street] = {};
    currentData[walk][street].street_weight = streetWeight;

    // 5. Update Storage based on Value
    if (newValue === 'n') {
        const streetObject = currentData[walk][street];
        Object.keys(streetObject).forEach(key => {
            if (streetObject[key] && typeof streetObject[key] === 'object' && streetObject[key].tags) {
                streetObject[key].tags[code] = 'n';
            }
        });
        console.log(`🚫 Street ${street} wiped to 'n'`);
    } else {
        if (!currentData[walk][street][house]) {
            currentData[walk][street][house] = { votes: "0", tags: {} };
        }
        if (!currentData[walk][street][house].tags) {
            currentData[walk][street][house].tags = {};
        }
        currentData[walk][street][house].tags[code] = 'y';
        console.log(`✅ Tag ${code} set for House ${house} on ${street}`);
    }

    // 6. Global Metadata & PERSISTENCE
    currentData[walk][street].ts = Date.now();

    // --- THE VITAL SAVE STEP ---
    window.BAKED_DATA = currentData;
    if (typeof saveBakedData === 'function') {
        saveBakedData(currentData);
    }

    // ⚡️ TRIGGER: Recalculate
    if (window.updateWalkVisuals) {
        window.updateWalkVisuals(walk, code);
    } else if (parent.updateWalkVisuals) {
        parent.updateWalkVisuals(walk, code);
    }
};

window.updateMarkerStatus = function(region_id) {
    if (!region_id) return;

    // Use the helper to find the data regardless of scope
    const currentData = getBakedData();
    const regionData = currentData[region_id] || {};

    let completedUnits = 0;
    Object.values(regionData).forEach(unit => {
        if (parseInt(unit.votes) > 0) completedUnits++;
    });

    let expectedHouses = 0;

    // Check both local and parent scope for the map instance

    // Standardize: Look for fmap locally, then on parent, then on top
        const activeMap = window.fmap || parent.fmap || (document.getElementById('iframe1') && document.getElementById('iframe1').contentWindow.fmap);

        if (!activeMap) {
            console.warn("fmap not found. Is iframe1 loaded yet?");
            return;
        }

        // Now use activeMap instead of fmap or activeMap    var activeMap = window.fmap || parent.fmap;

    if (activeMap) {
        // A. Find the polygon using activeMap, NOT 'map'
        activeMap.eachLayer(function(layer) {
            if (layer.feature && layer.feature.properties && layer.feature.properties.region_id === region_id) {
                expectedHouses = layer.feature.properties.expected_houses || 0;
            }
        });
    } else {
        console.error("The 'map' variable is still undefined!");
        return;
    }


    // C. Determine Color logic
    // Green: All houses have at least 1 vote
    // Yellow: Some houses have votes
    // Null/Original: No activity

    const healthColor = (completedUnits >= expectedHouses && expectedHouses > 0) ? "#28a745" :
                        (completedUnits > 0 ? "#ffcc00" : null);

    // Update Label
    const labelSpan = document.getElementById(`label-${region_id}`);
    if (labelSpan) {
        if (healthColor) {
            labelSpan.style.background = healthColor;
            labelSpan.style.color = "white";
        } else {
            // Restore original zone color if no votes (requires storing original fcol)
            // For now, let's just keep it visible
        }
    }

    // B. Update the Polygon using activeMap
    activeMap.eachLayer(function(layer) {
        if (layer.feature && layer.feature.properties && layer.feature.properties.region_id === region_id) {
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

window.updateWalkVisuals = function(region_id, targetTag = 'L1') {
    console.group(`🔎 GHOST UPDATE: ${region_id} [${targetTag}]`);

    const activeMap = window.fmap || parent.fmap;
    const Leaflet = window.L || parent.L;
    const cleanId = String(region_id).trim();

    // --- 1. DATA INITIALIZATION ---
    const fullData = typeof getBakedData === 'function' ? getBakedData() : (window.BAKED_DATA || {});

    // Initialize fresh state if region doesn't exist yet to prevent script from falling over
    let regionData = fullData[cleanId];
    if (!regionData) {
        console.warn(`⚠️ Initializing fresh data state for ${cleanId}`);
        regionData = { region_total_houses: 0 };
    }

    // --- 2. MATH (Denominator & Numerator) ---
    let completedWeight = 0;
    let totalPossible = regionData.region_total_houses || 0;

    // Denominator Fallback: Query map if Baked Data total is missing
    if (totalPossible === 0) {
        activeMap.eachLayer(l => {
            if (l.feature?.properties?.region_id === cleanId && !l.is_ghost) {
                totalPossible = parseInt(l.feature.properties.expected_houses || 0);
            }
        });
    }

    // Numerator Calculation: Sum weights of tagged streets
    Object.values(regionData).forEach(street => {
        if (street && typeof street === 'object' && street.street_weight) {
            const isTagged = Object.values(street).some(unit => unit?.tags?.[targetTag] === 'y');
            if (isTagged) {
                completedWeight += street.street_weight;
            }
        }
    });

    const pct = totalPossible > 0 ? (completedWeight / totalPossible) : 0;
    const finalOpacity = 0.8 * pct;

    console.log(`📊 Math: ${completedWeight} / ${totalPossible} = ${(pct * 100).toFixed(1)}% | Opacity: ${finalOpacity.toFixed(2)}`);

    (function safeInterrogate() {
    const iframe = document.getElementById('iframe1');
    const mapWin = iframe ? iframe.contentWindow : window;

    // 1. Find the Control Instance
    let lcKey = Object.keys(mapWin).find(k => k.startsWith('layer_control_'));
    let lc = mapWin[lcKey];

    if (!lc || !lc._layers) {
        return console.error("❌ Layer Control or _layers dictionary is missing.");
    }

    console.log("--- 📂 TARGET OBJECT INTERROGATION ---");

    const layers = lc._layers;
    for (let id in layers) {
        // SAFETY: Skip if the entry or the name property is missing
        if (!layers[id] || typeof layers[id].name !== 'string') continue;

        if (layers[id].name.includes('[L1]')) {
            const bucket = layers[id].layer;
            console.group(`🎯 Found Bucket: ${layers[id].name}`);
            console.log("Constructor:", bucket ? bucket.constructor.name : "NULL");
            console.log("Leaflet ID:", id);

            if (bucket) {
                console.log("Properties:", Object.keys(bucket));
                console.log("Internal Children (_layers):", bucket._layers);
                // Check for your Python metadata
                console.log("Python 'mytag':", bucket.mytag || "Not Found");

                // Inspect the Prototype (Inheritance)
                let proto = Object.getPrototypeOf(bucket);
                console.log("Inherits From:", proto.constructor.name);
            }
            console.groupEnd();
        }
    }
})();

    // --- 3. DICTIONARY SEARCH (Targeting the Iframe) ---
    const findBucket = () => {
        // 1. Get the iframe window
        const iframe = document.getElementById('iframe1'); // Ensure this ID matches your iframe
        const mapWin = iframe ? iframe.contentWindow : window;

        // 2. Search THAT window's variables
        for (const key in mapWin) {
            if (key.startsWith("layer_control_")) {
                const layers = mapWin[key].overlays || mapWin[key]._layers;
                for (const name in layers) {
                    if (name.includes(`[${targetTag}]`)) {
                        return layers[name].layer || layers[name];
                    }
                }
            }
        }
        return null;
    };
    let targetGroup = findBucket();

    if (!targetGroup) {
        console.error(`❌ Bucket [${targetTag}] not found in Layer Control.`);
        console.groupEnd();
        return;
    }

    // --- 4. DRAWING & STRICT PARENTING ---
    activeMap.eachLayer(layer => {
        if (layer.feature?.properties?.region_id === cleanId && !layer.is_ghost) {
            const ghostKey = `_ghost_${targetTag}`;

            // 1. Creation (Only runs once)
            if (!layer[ghostKey]) {
                console.log(`🏗️ Creating Ghost and locking to Bucket [${targetTag}]`);

                // Clone geometry to ensure independence
                const geometry = JSON.parse(JSON.stringify(layer.feature.geometry));

                layer[ghostKey] = Leaflet.geoJSON({
                    type: "Feature",
                    geometry: geometry,
                    properties: { is_ghost: true }
                }, {
                    pane: 'overlayPane',
                    style: {
                        color: "transparent",
                        fillColor: (targetTag.startsWith('L') ? "#333" : "#800080"),
                        fillOpacity: finalOpacity,
                        interactive: false
                    }
                });

                layer[ghostKey].is_ghost = true;

                // 🔗 THE ONLY CONNECTION:
                // Add the ghost to the group. DO NOT call .addTo(activeMap).
                targetGroup.addLayer(layer[ghostKey]);
            }

            // 2. Update Style
            try {
                layer[ghostKey].setStyle({ fillOpacity: finalOpacity });

                // 🔄 FORCED SYNC:
                // If the user just toggled the checkbox, Leaflet might need a nudge
                // to show layers that were added while the group was hidden.
                if (activeMap.hasLayer(targetGroup)) {
                    if (!activeMap.hasLayer(layer[ghostKey])) {
                        layer[ghostKey].addTo(activeMap);
                    }
                } else {
                    if (activeMap.hasLayer(layer[ghostKey])) {
                        activeMap.removeLayer(layer[ghostKey]);
                    }
                }
            } catch (e) {
                console.warn("⏳ Sync postponed: Renderer is re-indexing.");
            }
        }
    });

    console.groupEnd();
};

window.incrementVoteCount = function(btn) {
    console.log("➕ incrementVoteCount clicked");
    var count = parseInt(btn.getAttribute('data-count')) || 0;
    var max = parseInt(btn.getAttribute('data-max')) || 1;
    currentData = getBakedData()

    // Cycle count: 0 -> 1 -> 2 -> 0
    count = (count + 1) > max ? 0 : count + 1;

    btn.setAttribute('data-count', count);
    btn.innerText = count + '/' + max;

    var row = btn.closest('.canvass-row');

    if (row) {
        // 1. Grab all three identifiers
        var walk = row.getAttribute('data-walk');     // e.g., "N267"
        var street = row.getAttribute('data-street'); // e.g., "FOXLEIGH_GRANGE"
        var houseSelector = row.querySelector('.unit-selector');
        var viSelector = row.querySelector('.vi-selector');

        if (houseSelector) {
            var house = houseSelector.value;
            var vi = viSelector ? viSelector.value : "";

            // 2. Ensure the 3-tier hierarchy exists in memory
            if (!currentData[walk]) currentData[walk] = {};
            if (!currentData[walk][street]) currentData[walk][street] = {};

            // 3. Update the specific house entry
            // We preserve existing tags if they exist by merging
            var existingData = currentData[walk][street][house] || {};

            currentData[walk][street][house] = {
                ...existingData, // Keep tags and other metadata
                vi: vi,
                votes: count.toString(),
                ts: Date.now()
            };

            console.log(`💾 Saved to memory: [${walk}] ${street} No. ${house} = ${count} votes`);

            // --- REFRESH UI ---
            window.refreshDropdownColors(houseSelector);
            window.updateRowAppearance(row, count, max);

            // --- REFRESH MAP MARKER ---
            // Important: We still pass 'street' to updateMarkerStatus if
            // your map uses street names as the keys for markers.
            if (window.updateMarkerStatus) {
                window.updateMarkerStatus(street);
            }
        }
    }
};

window.deployUpdate = function() {

//    if (!confirm("⚠️ Save and Deploy to Server?")) return;

    // Start with a clean local object for this specific "scrape"
    // This prevents the old flat structure from 'polluting' the new save
    const updatedData = {};

    // If parent has data, we merge into it to keep other walks safe
    const masterData = getBakedData();

    document.querySelectorAll('.canvass-row').forEach(row => {
        const walk = row.getAttribute('data-walk');
        const street = row.getAttribute('data-street');
        const house = row.querySelector('.unit-selector').value;
        const vi = row.querySelector('.vi-selector').value;
        const votes = row.querySelector('.vote-btn').getAttribute('data-count');
        const pd = row.getAttribute('data-district');

        // CRITICAL CHECK:
        if (!walk || walk === "None" || walk === "") {
            console.error(`MISSING WALK for ${street}. Check Python injection.`);
            return;
        }

        // Initialize levels in our temporary object
        if (!updatedData[walk]) updatedData[walk] = {};
        if (!updatedData[walk][street]) updatedData[walk][street] = {};

        updatedData[walk][street][house] = {
            vi: vi,
            votes: votes,
            pd: pd,
            ts: Date.now()
        };
    });

    // Deep merge the updatedData into masterData
    for (let w in updatedData) {
        if (!masterData[w]) masterData[w] = {};
        for (let s in updatedData[w]) {
            masterData[w][s] = updatedData[w][s];
        }
    }

    console.log("FINAL OBJECT TO BE SENT:");
    console.dir(masterData);

    fetch('/upload_data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(masterData)
    })
    .then(res => res.json())
    .then(result => {
//        alert("✅ Success! Check baked_data.json now.");
        if (parent) parent.BAKED_DATA = masterData;
    })
    .catch(err => alert("❌ Save failed."));
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
    const walk = row.getAttribute('data-walk');
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
        var walk = row.getAttribute('data-walk');
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
    var walk = row.getAttribute('data-walk');
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
