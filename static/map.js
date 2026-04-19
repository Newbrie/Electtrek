/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

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

var BAKED_DATA = BAKED_DATA || {};

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

window.updateElectorTag = function(street, unit, code, isActive) {
    if (!window.BAKED_DATA[street]) return;
    if (!window.BAKED_DATA[street][unit]) window.BAKED_DATA[street][unit] = { votes: 0, tags: "" };

    let currentTags = window.BAKED_DATA[street][unit].tags || "";
    let tagList = currentTags.split(',').filter(t => t.trim() !== "");

    if (isActive) {
        if (!tagList.includes(code)) tagList.push(code);
    } else {
        tagList = tagList.filter(t => t !== code);
    }

    window.BAKED_DATA[street][unit].tags = tagList.join(',');
    console.log(`Updated ${street} ${unit} tags: ${window.BAKED_DATA[street][unit].tags}`);
};

window.updateMarkerStatus = function(region_id) {
    if (!region_id) return;

    let completedUnits = 0;
    let expectedHouses = 0;

    // A. Find the polygon to get the "expected" house count
    map.eachLayer(function(layer) {
        if (layer.feature && layer.feature.properties && layer.feature.properties.region_id === region_id) {
            expectedHouses = layer.feature.properties.expected_houses || 0;
        }
    });

    // B. Count how many unique houses in BAKED_DATA have votes
    if (window.BAKED_DATA[region_id]) {
        Object.values(window.BAKED_DATA[region_id]).forEach(unit => {
            if (parseInt(unit.votes) > 0) completedUnits++;
        });
    }

    // C. Determine Color logic
    // Green: All houses have at least 1 vote
    // Yellow: Some houses have votes
    // Null/Original: No activity
    const healthColor = (completedUnits >= expectedHouses && expectedHouses > 0) ? "#28a745" :
                        (completedUnits > 0 ? "#ffcc00" : null);

    // D. Update Label
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

    // E. Update Polygon
    map.eachLayer(function(layer) {
        if (layer.feature && layer.feature.properties && layer.feature.properties.region_id === region_id) {
            if (healthColor) {
                layer.setStyle({ fillColor: healthColor, fillOpacity: 0.6 });
            } else {
                // If votes cleared, reset to original style (optional)
                layer.setStyle({ fillOpacity: 0.4 });
            }
        }
    });
};

window.loadHouseData = function(selectElement) {
    console.log("🏠 loadHouseData triggered for:", selectElement.value);
    var row = selectElement.closest('.canvass-row');
    if (!row) return;

    var street = row.getAttribute('data-street');
    var house = selectElement.value;
    var opt = selectElement.options[selectElement.selectedIndex];
    var max = parseInt(opt.getAttribute('data-max')) || 1;

    var record = (BAKED_DATA[street] && BAKED_DATA[street][house]) ? BAKED_DATA[street][house] : null;
    var btn = row.querySelector('.vote-btn');

    btn.setAttribute('data-max', max);
    if (record) {
        btn.setAttribute('data-count', record.votes);
        btn.innerText = record.votes + '/' + max;
    } else {
        btn.setAttribute('data-count', '0');
        btn.innerText = '0/' + max;
    }

    // After setting the data, refresh the colors of the list
    window.refreshDropdownColors(selectElement);

    window.updateRowAppearance(row, count, max);
    window.updateMarkerStatus(selectElement.ownerDocument);

};

window.incrementVoteCount = function(btn) {
    console.log("➕ incrementVoteCount clicked");
    var count = parseInt(btn.getAttribute('data-count')) || 0;
    var max = parseInt(btn.getAttribute('data-max')) || 1;

    count = (count + 1) > max ? 0 : count + 1;

    btn.setAttribute('data-count', count);
    btn.innerText = count + '/' + max;

    var row = btn.closest('.canvass-row');

    if (row) {
        var street = row.getAttribute('data-street'); // This is your Region ID
        var houseSelector = row.querySelector('.unit-selector');
        var viSelector = row.querySelector('.vi-selector');

        if (houseSelector) {
            var house = houseSelector.value;
            var vi = viSelector ? viSelector.value : "";

            if (!BAKED_DATA[street]) BAKED_DATA[street] = {};

            // Update the central ledger
            BAKED_DATA[street][house] = {
                vi: vi,
                votes: count.toString(),
                ts: Date.now()
            };
            console.log(`💾 Saved to memory: ${street} No. ${house} = ${count} votes`);

            // --- REFRESH UI ---
            window.refreshDropdownColors(houseSelector);
            window.updateRowAppearance(row, count, max);

            // --- REFRESH MAP MARKER ---
            // Pass the street name/ID so the marker knows to change color
            if (window.updateMarkerStatus) {
                window.updateMarkerStatus(street);
            }
        }
    }
};

// --- SAVE SYSTEM ---
var deployUpdate = function(doc) {
    var targetDoc = doc || document;

    targetDoc.querySelectorAll('.canvass-row').forEach(function(row) {
        var street = row.getAttribute('data-street');
        var house = row.querySelector('.unit-selector').value;
        var vi = row.querySelector('.vi-selector').value;
        var votes = row.querySelector('.vote-btn').getAttribute('data-count');

        if (!BAKED_DATA[street]) BAKED_DATA[street] = {};
        BAKED_DATA[street][house] = { vi: vi, votes: votes, ts: Date.now() };
    });

    var jsonString = JSON.stringify(BAKED_DATA);
    var fullHtml = document.documentElement.outerHTML;

    var newHtml = fullHtml.replace(/var BAKED_DATA\s*=\s*[^;]+;/, 'var BAKED_DATA = ' + jsonString + ';');

    var blob = new Blob(["<!DOCTYPE html>\n" + newHtml], { type: 'text/html' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = "Canvass_Sheet_Updated.html";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
};


function bindEvent(element, eventName, eventHandler) {
  element.addEventListener(eventName, eventHandler, false);
}

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


function updateMessages() {
  const old = pessages.pop();
  const ul = parent.document.getElementById("logwin");
  const li = parent.document.createElement("li");

  const tabletitle = parent.document.getElementById("tabletitle");
  const table = parent.document.getElementById("captains-table");

  const tabtitle = parent.document.getElementById("selectedTitle");
  const tabhead = table.querySelector("thead");
  const tabbody = table.querySelector("tbody");

  // Update the <h2> to match the current selection
  const tableSelector = tabletitle.querySelector("#tableSelector");
  const selectedText = tableSelector.options[tableSelector.selectedIndex].text;
  tabtitle.textContent = `Details for: ${selectedText}`;


// Define your party color lookup
const VCO = {
    "O": "brown", "R": "cyan", "C": "blue", "S": "red",
    "LD": "yellow", "G": "limegreen", "I": "indigo",
    "PC": "darkred", "SD": "orange", "Z": "lightgray",
    "W": "white", "X": "darkgray"
};
//  fetchAndUpdateChart();

fetch(`/displayareas`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin"
})
.then(response => response.json())
.then(data => {
    console.log("Display Data received:", data);

    if (!Array.isArray(data) || data.length < 3) {
        console.error("Invalid or incomplete data:", data);
        return;
    }

    // --- FIX 1: Ensure these variable names match your earlier definitions ---
    // If you used 'tabHead' earlier, use 'tabHead' here.
    // I am assuming you have these defined at the top of your function:
    const tabtitle = document.getElementById("selectedTitle");
    const tabhead = document.querySelector("#captains-table thead");
    const tabbody = document.querySelector("#captains-table tbody");
    const yourparty = document.getElementById("yourparty");

    if (!tabhead || !tabbody || !tabtitle) {
        console.error("❌ Table elements not found in DOM");
        return;
    }

    const columnHeaders = data[0];
    const rows = data[1];
    const title = data[2];

    // Clear previous content
    tabtitle.innerHTML = title;
    tabhead.innerHTML = "";
    tabbody.innerHTML = "";

    // Build table head row
    const headRow = document.createElement("tr");
    const checkboxHeader = document.createElement("th");
    checkboxHeader.textContent = "?";
    headRow.appendChild(checkboxHeader);

    columnHeaders.forEach(header => {
        if (header === "nid") return; // Skip NID in the header too!
        const th = document.createElement("th");
        th.textContent = header.toUpperCase();
        headRow.appendChild(th);
    });
    tabhead.appendChild(headRow);

    // Build table body
    rows.forEach(record => {
        const row = document.createElement("tr");

        // Checkbox Cell
        const checkboxCell = document.createElement("td");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.name = "selectRow[]";
        checkbox.classList.add("selectRow");

        // 🎯 The NID fix
        const nidValue = record.nid || "";
        checkbox.value = nidValue;
        checkbox.setAttribute('data-nid', nidValue);

        checkboxCell.appendChild(checkbox);
        row.appendChild(checkboxCell);

        // Data Cells
        columnHeaders.forEach(header => {
            if (header === "nid") return;

            const cell = document.createElement("td");
            const value = record[header] !== undefined ? record[header] : "";
            cell.innerHTML = value;

            // Highlight Party
            if (yourparty && header === yourparty.value) {
                // Ensure VCO is defined globally
                const color = (typeof VCO !== 'undefined') ? VCO[yourparty.value] : "inherit";
                cell.style.backgroundColor = color;
            }

            row.appendChild(cell);
        });

        tabbody.appendChild(row);
    });
})
.catch(error => console.error("Elector Table Fetch error:", error));
// --- FIX 2: Removed the stray braces that were causing the syntax error ---

li.appendChild(parent.document.createTextNode(old + ":completed"));
ul.appendChild(li);
};



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
    var row = selectElement.closest('.canvass-row');
    if (!row) return;

    var street = row.getAttribute('data-street');
    var house = selectElement.value;
    var opt = selectElement.options[selectElement.selectedIndex];
    var max = parseInt(opt.getAttribute('data-max')) || 1;

    // 1. Fetch the record for this SPECIFIC house
    var record = (BAKED_DATA[street] && BAKED_DATA[street][house]) ? BAKED_DATA[street][house] : null;
    var btn = row.querySelector('.vote-btn');
    var viSelector = row.querySelector('.vi-selector');

    // 2. Update Button and Selectors BEFORE coloring
    btn.setAttribute('data-max', max);
    if (record) {
        if (viSelector) viSelector.value = record.vi;
        btn.setAttribute('data-count', record.votes);
        btn.innerText = record.votes + '/' + max;
    } else {
        if (viSelector) viSelector.selectedIndex = 0;
        btn.setAttribute('data-count', '0');
        btn.innerText = '0/' + max;
    }

    // 3. FORCE RE-COLORING
    // Get the fresh count we just set
    const currentCount = parseInt(btn.getAttribute('data-count')) || 0;

    // This updates the Row background and the Button background
    window.updateRowAppearance(row, currentCount, max);

    // This updates the Dropdown's own color AND all the options inside it
    window.refreshDropdownColors(selectElement);

    // Finally, check if the map marker should change
    window.updateMarkerStatus(selectElement.ownerDocument);
};

window.updateTagToggles = function(sel) {
    const row = sel.closest('tr');
    if (!row) return;

    const street = row.getAttribute('data-street');
    const unit = sel.value;

    // Access the central data store
    const baked = (window.BAKED_DATA && window.BAKED_DATA[street]) ? window.BAKED_DATA[street][unit] : null;

    // --- NEW: Sync the VI Selector Color ---
    const viSel = row.querySelector('.vi-selector');
    if (viSel) {
        // Update the value to what's in BAKED_DATA (or default to empty)
        viSel.value = (baked && baked.vi) ? baked.vi : "";
        // Manually trigger the color refresh
        if (window.refreshDropdownColors) {
            window.refreshDropdownColors(viSel);
        }
    }

    // --- Existing Tag Logic ---
    const currentTags = (baked && baked.tags) ? baked.tags.split(',') : [];
    row.querySelectorAll('.tag-toggle').forEach(span => {
        const code = span.getAttribute('data-code');
        const hasTag = currentTags.includes(code);
        span.innerText = hasTag ? 'y' : 'n';
        span.className = 'tag-toggle ' + (hasTag ? 'tag-active' : 'tag-inactive');
    });
};

window.refreshDropdownColors = function(selectElement) {
    if (!selectElement) return;
    var row = selectElement.closest('.canvass-row') || selectElement.closest('tr');
    if (!row) return;

    // Check which dropdown we are dealing with
    const isUnitSelector = selectElement.classList.contains('unit-selector');
    const isVISelector = selectElement.classList.contains('vi-selector');

    // --- LOGIC A: UNIT SELECTOR (Vote Counts) ---
    if (isUnitSelector) {
        var street = row.getAttribute('data-street');
        Array.from(selectElement.options).forEach(opt => {
            var h = opt.value;
            var m = parseInt(opt.getAttribute('data-max')) || 1;
            var rec = (BAKED_DATA[street] && BAKED_DATA[street][h]) ? BAKED_DATA[street][h] : null;
            var v = rec ? parseInt(rec.votes) : 0;

            if (v >= m && m > 0) {
                opt.text = h + " ✅";
                opt.style.color = "#28a745";
            } else if (v > 0) {
                opt.text = h + " 🟡";
                opt.style.color = "#ffcc00";
            } else {
                opt.text = h;
                opt.style.color = "";
            }
        });

        // Color the face of the Unit Dropdown
        const btn = row.querySelector('.vote-btn');
        const cv = parseInt(btn.getAttribute('data-count')) || 0;
        const cm = parseInt(btn.getAttribute('data-max')) || 1;
        selectElement.style.backgroundColor = (cv >= cm && cm > 0) ? "#28a745" : (cv > 0 ? "#ffcc00" : "");
        selectElement.style.color = (cv >= cm && cm > 0) ? "white" : (cv > 0 ? "black" : "");
    }

    // --- LOGIC B: VI SELECTOR (Political Intent Colors) ---
    if (isVISelector) {
        const val = selectElement.value;
        const colors = {
            '1': '#28a745', // Strong Green
            '2': '#94d3a2', // Light Green
            '3': '#ffffcc', // Yellow
            '4': '#ffcccc', // Light Red
            '5': '#dc3545'  // Dark Red
        };
        selectElement.style.backgroundColor = colors[val] || '#ffffff';
        selectElement.style.color = (val === '1' || val === '5') ? 'white' : 'black';
    }
};

window.updateVI = function(selectElement) {
    var row = selectElement.closest('.canvass-row') || selectElement.closest('tr');
    var street = row.getAttribute('data-street');
    var house = row.querySelector('.unit-selector').value;

    if (!BAKED_DATA[street]) BAKED_DATA[street] = {};
    if (!BAKED_DATA[street][house]) BAKED_DATA[street][house] = { votes: 0, tags: "" };

    // Update only the VI and timestamp
    BAKED_DATA[street][house].vi = selectElement.value;
    BAKED_DATA[street][house].ts = Date.now();

    // Re-color the dropdown immediately
    window.refreshDropdownColors(selectElement);

    // --- NEW: Trigger the Map Marker/Polygon refresh ---
    if (window.updateMarkerStatus) {
        window.updateMarkerStatus(street);
    }

    console.log(`📝 Saved Intent for ${street} ${house}: ${selectElement.value}`);
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
