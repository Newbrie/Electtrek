/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

var pack = window.flaskMessages ;

// Now you can loop through them or push them to your array
const pessages = [];
if (pack && pack.length > 0) {
    pack.forEach(msg => {
        pessages.push(msg);
        console.log("Flash Message:", msg);
    });
}

window.activeSlotId = null;

// 🌟 UNIFIED INTERCOM GATEWAY (Handles all incoming iframe messages in one place)
window.addEventListener('message', function (e) {
    // ---------------------------------------------------------
    // 1. RUN REGULAR LOGGING & UI RE-STRIPING (Your original bindEvent logic)
    // ---------------------------------------------------------
    if (typeof pessages !== 'undefined') {
        pessages.pop();
        pessages.push(e.data);
    }

    var ul = document.getElementById("logwin");
    if (ul) {
        var li = document.createElement("li");
        li.appendChild(document.createTextNode(e.data));
        ul.appendChild(li);
        console.log("✅ Successfully appended location row to UI.");
    } else {
        console.warn("ℹ️ UI container element was not found on this page layout. Location update skipped.");
    }
    console.log("_____FlashPostedmessage: ", e.data);

    // ---------------------------------------------------------
    // 2. INTERCEPT SPECIFIC ACTION COMMANDS (Your new synchronization logic)
    // ---------------------------------------------------------
    if (e.data === 'TRIGGER_PARENT_SYNC_CLOSE') {
        console.log("📥 [PARENT RECEIVER] Caught closure request from iframe. Directing to sync routing engine...");

        if (typeof window.handleModalCloseSequence === 'function') {
            window.handleModalCloseSequence();
        } else {
            console.error("💥 Critical: window.handleModalCloseSequence is not defined on the parent window map scope.");
        }
    }
});


var moveDown = function (msg, area) {
    window.parent.postMessage({ type: `Drilling down to next level within ${area}`}, '*');

    const ul = parent.document.getElementById("logwin");
    if (ul) ul.scrollTop = ul.scrollHeight;
    window.location.assign(msg);
//    alert("Submitting to: " + msg);

};


var moveUp = function (msg,area) {
  // Send a message to the parent
      window.parent.postMessage({ type:"Moving up to "+ area + " level "}, '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = ul.scrollHeight;

      };
var showMore = function (msg,area) {
  // Send a message to the parent
      window.parent.postMessage({ type: "Showing the level within "+ area}, '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = ul.scrollHeight;
      };

      /* When the user clicks on the button,
      toggle between hiding and showing the dropdown content */


  function openSlotModal(slotId) {
      currentSlotId = slotId;
      const slotDiv = document.querySelector(`.slot[data-id="${slotId}"]`);

      // --- 🔴 HIGHLIGHT LOGIC START ---
      // 1. Remove the red outline from any previously highlighted slot
      document.querySelectorAll(".slot.selected-slot").forEach(s => {
          s.classList.remove("selected-slot");
      });

      // 2. Set this slot as the active one and apply the red line class
      if (slotDiv) {
          window.activeSlotId = slotId;
          slotDiv.classList.add("selected-slot");
      }
      // --- 🔴 HIGHLIGHT LOGIC END ---

      // Ensure slot exists in calendarData
      if (!calendarData[slotId]) calendarData[slotId] = {};
      const data = calendarData[slotId]; // Reference, not copy

      // Fill dropdowns
      fillSelect("resourcesSelect", window.resources);
      fillSelect("placeSelect", window.places);
      console.log("💾 filled resources:", window.resources);

      // Ensure data structures exist
      if (!data.resources) data.resources = [];

      // Infer missing fields individually from DOM lozenges if not already set
      if (slotDiv) {
          const lozenges = Array.from(slotDiv.querySelectorAll(".lozenge"));
          lozenges.forEach(l => {
              const type = l.dataset.type;
              const code = l.dataset.code || l.textContent.trim();

              if (!code || code === "undefined" || code === "null") return;

              if (type === "activity" && !data.activity) {
                  data.activity = code;
              } else if (type === "place" && !data.place) {
                  data.place = code;
              } else if (type === "area" && !data.area) {
                  data.area = code;
              } else if (type === "resource" && !data.resources.includes(code)) {
                  data.resources.push(code);
              }
          });
      }

      // 🌳 Render tree selectors now that the modal DOM / containers exist
      if (window.areaTree && typeof renderTreeSelector === "function") {
          renderTreeSelector(window.areaTree, {
              containerId: 'areaAccordionContainer',
              accordionId: 'areaSelectAccordion',
              emptyMessage: 'No areas available for this map',
              allLabel: name => `All of ${name}`,
              createButton: createAreaButton
          });
      }

      if (window.taskTree && typeof renderTreeSelector === "function") {
          renderTreeSelector(window.taskTree, {
              containerId: 'taskAccordionContainer',
              accordionId: 'taskSelectAccordion',
              emptyMessage: 'No task types available for this map',
              allLabel: name => `All of ${name}`,
              createButton: createTaskButton
          });
      }

      // Pre-select dropdowns
      document.getElementById("activitySelect").value = data.activity || "";
      document.getElementById("placeSelect").value = data.place || "";
      document.getElementById("areaSelect").value = data.area || "";

      const resSel = document.getElementById("resourcesSelect");
      Array.from(resSel.options).forEach(opt => {
          opt.selected = data.resources?.includes(opt.value) || false;
      });

      // Show modal
      const modalInstance = new bootstrap.Modal(document.getElementById("slotModal"));
      modalInstance.show();
  }




  function createStandaloneHTML() {
      const doctype = "<!DOCTYPE html>\n";
      const clone = document.documentElement.cloneNode(true);
      const currentData = getBakedData();

      // 1. Cleanup
      const calendar = clone.querySelector("#calendar-grid");
      if (calendar) calendar.innerHTML = "";

      // 2. Data Preparation
      // We pull the current election data that was loaded from CE.calendar_plan
      // Assuming your JS variable is named 'currentElection' or similar
      const bakedDataStr = JSON.stringify(currentData || {});
      const calendarPlanStr = JSON.stringify(window.currentElection?.calendar_plan || []);

      // 3. The Injection String
      const dataInjection = `
      <script>
          // This simulates the CE.calendar_plan from your Python object
          currentData = ${bakedDataStr};
          window.currentElection = {
              calendar_plan: ${calendarPlanStr}
          };
          console.log("Election data and Calendar plan baked into standalone.");
      </script>
      `;

      // 4. Final Assembly
      let htmlString = clone.outerHTML;
      htmlString = htmlString.replace("</head>", dataInjection + "</head>");

      const FINAL_API_URL = DEVURLS['prod'];
      htmlString = doctype + htmlString.replace(/__REPLACE_WITH_API_URL__/g, FINAL_API_URL);

      return htmlString;
    }



    // Format hours nicely
    function formatHour(hour) {
      const ampm = hour >= 12 ? "PM" : "AM";
      const h = (hour % 12) || 12;
      return `${h} ${ampm}`;
    }


    // Build 45-day x 2-hour grid
    function buildCalendarGrid(containerId, daysToShow = 45) {
      const container = document.getElementById(containerId);

      // 👇 Guard check: Exit safely if the container isn't in the DOM yet
      if (!container) {
          console.warn(`⚠️ Calendar container #${containerId} not found in DOM. Skipping grid build.`);
          return;
      }

      container.innerHTML = "";

      const slots = ["9 AM", "11 AM", "1 PM", "3 PM", "5 PM", "7 PM"];

      // ─── Date Setup ─────────────────────────────────────────────────────────
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      // ⬇️ Find Monday of the previous week
      const dayOfWeek = today.getDay(); // 0 (Sun) to 6 (Sat)
      const daysSinceMonday = (dayOfWeek + 6) % 7 + 7;
      const startDate = new Date(today);
      startDate.setDate(today.getDate() - daysSinceMonday);

      // ✅ Store globally for access elsewhere
      window.calendarStartDate = new Date(startDate);

      // ─── Election Date (optional) ────────────────────────────────────────────
      let electionDate = null;
      const electionDateStr = window.document?.getElementById('electiondate')?.value;

      if (electionDateStr) {
        const [year, month, day] = electionDateStr.split("-");
        electionDate = new Date(year, month - 1, day);
        electionDate.setHours(0, 0, 0, 0);
        console.log("📅 Election date parsed as:", electionDate.toDateString());
      } else {
        console.warn("⚠️ No election date found");
      }

      // ─── Calculate padding and total days ──────────────────────────────────
      const padStart = startDate.getDay() === 0 ? 6 : startDate.getDay() - 1;
      const padEnd = 7 - ((padStart + daysToShow) % 7);
      const totalDays = daysToShow + padStart + (padEnd === 7 ? 0 : padEnd);

      let weekRow = document.createElement("div");
      weekRow.className = "week-row";

      for (let i = 0; i < totalDays; i++) {
        const dayDiv = document.createElement("div");
        dayDiv.className = "day-column";

        // Determine if this is a blank cell
        if (i < padStart || i >= padStart + daysToShow) {
          dayDiv.classList.add("empty-day"); // 👈 add class for styling
        } else {
          // Calculate the correct date for this cell
          const date = new Date(startDate);
          date.setDate(startDate.getDate() + (i - padStart));

          // Apply highlights
          if (date.getTime() === today.getTime()) dayDiv.classList.add("today-highlight");
          if (electionDate && date.getTime() === electionDate.getTime()) dayDiv.classList.add("election-highlight");

          // Day header
          const dayNumber = date.getDate();
          const weekday = date.toLocaleDateString(undefined, { weekday: "short" });

          const header = document.createElement("div");
          header.className = "day-header";
          header.textContent = `${weekday} ${dayNumber}`;
          dayDiv.appendChild(header);

          // Create slots
          for (const slotName of slots) {
            const slotDiv = document.createElement("div");
            slotDiv.className = "slot";
            slotDiv.dataset.availability = "0";
            slotDiv.dataset.time = slotName;

            const localDateStr = date.toLocaleDateString("en-CA"); // YYYY-MM-DD
            const slotId = `${localDateStr}_${slotName}`;
            slotDiv.dataset.id = slotId;

            const timeLabel = document.createElement("div");
            timeLabel.className = "slot-label";
            timeLabel.textContent = slotName;
            slotDiv.appendChild(timeLabel);

            const lozengeContainer = document.createElement("div");
            lozengeContainer.className = "lozenge-container";
            slotDiv.appendChild(lozengeContainer);

            slotDiv.addEventListener("click", () => openSlotModal(slotId));
            dayDiv.appendChild(slotDiv);
          }

        }

        weekRow.appendChild(dayDiv);

        // Finish a week row after 7 days
        if ((i + 1) % 7 === 0) {
          container.appendChild(weekRow);
          weekRow = document.createElement("div");
          weekRow.className = "week-row";
        }
      }

      if (weekRow.children.length) {
        container.appendChild(weekRow);
      }
      console.log("📅 Calendar-Grid:", container);

    }
    // resourcing.js
    window.populateAllSelects = function(options = {}, constants = {}) {
        document.querySelectorAll("select").forEach(el => {
            const key = el.id;
            const items = options[key];
            if (!items) return;

            // skip special multi-selects
            if (el.multiple && key === "resources") return;

            // pass selected value if available
            const selectedValue = constants[key] ?? null;

            fillSelect(key, items, selectedValue);
        });
    };



  // Fill s
  window.populateDropdowns = function(options = {}) {
      fillSelect("activitySelect", window.task_tags);   // ✔ correct
      fillSelect("resourcesSelect", window.resources);
      fillSelect("placeSelect", window.places);
      fillSelect("areaSelect", window.areas);
  }

  window.fillSelect = function (selectId, items,selectedValue = null) {
        const sel = document.getElementById(selectId);
        if (!sel) return;

        sel.innerHTML = ""; // clear

        let arr = [];

        if (Array.isArray(items)) {
            arr = items.map(it => ({
                key: it.key ?? it,
                value: it.value ?? it
            }));
        } else if (typeof items === "object" && items !== null) {
            arr = Object.entries(items).map(([k, v]) => ({
                key: k,
                value: typeof v === "string" ? v : v?.name ?? v?.code ?? k
            }));
        }

        arr.forEach(it => {
            const opt = document.createElement("option");
            opt.value = it.key;
            opt.textContent = it.value;
            sel.appendChild(opt);
        });

        // ✅ Now safely set selected value
        if (selectedValue !== null) {
            sel.value = selectedValue;

            // fallback if value doesn't match exactly
            if (sel.value !== selectedValue) {
                const fallback = Array.from(sel.options).find(o => o.textContent === selectedValue);
                if (fallback) sel.value = fallback.value;
            }
        }
    }



  function updateSlotAvailability(slot) {
    // Count children with the Bootstrap resource lozenge class
    const resourceCount = [...slot.children].filter(child =>
      child.classList.contains('badge') && child.classList.contains('resource-lozenge')
    ).length;

    const availabilityLevel = Math.min(10, Math.ceil(resourceCount / 2));

    // Set a data attribute for styling or logic
    slot.setAttribute("data-availability", availabilityLevel);

    // Update tooltip text (Bootstrap tooltip)
    slot.setAttribute("title", `${availabilityLevel * 2} resources available`);

    // If using Bootstrap tooltips, refresh them
    if (slot._tooltipInstance) {
      slot._tooltipInstance.dispose(); // Remove old tooltip
    }
    slot._tooltipInstance = new bootstrap.Tooltip(slot); // Reinitialize tooltip
  }

  function processLozenges(lozenges, areas = {}, places = {}, tags = {}) {
    const resourceList = [];
    const activityList = [];
    const placeList = [];
    const areasList =[];

    lozenges?.forEach(loz => {
      if (!loz?.type || !loz?.code) {
        console.warn("Skipping invalid lozenge:", loz);
        return;
      }

      switch (loz.type) {
        case "resource":
          resourceList.push(loz.code);
          break;

        case "area": {
          const areaInfo = areas[loz.code];
          if (areaInfo?.details?.length) {
            areasList.push(`Area: ${loz.code} – ${areaInfo.details.join(", ")}`);
          } else {
            areasList.push(`Area: ${loz.code}`);
          }
          break;
        }

        case "place": {
          const placeInfo = places[loz.code];
          const tooltip = placeInfo?.tooltip || "(place unknown)";
          placeList.push(`${loz.code} – ${tooltip}`);
          break;
        }

        case "activity": {
          // For backward compatibility, fall back to tags if available
          const desc = tags[loz.code] || "(no description)";
          activityList.push(`${loz.code} – ${desc}`);
          break;
        }

        default:
          console.warn("Unknown lozenge type:", loz.type);
      }
    });

    return { resourceList, activityList, placeList, areasList };
  }


  function buildSummaryTable(slots, areas, places, tags) {
    const table = document.createElement("table");
    // Bootstrap table classes
    table.className = "table table-striped table-bordered table-hover table-sm";

    // Responsive wrapper
    const wrapper = document.createElement("div");
    wrapper.className = "table-responsive";
    wrapper.appendChild(table);

    table.innerHTML = `
      <thead class="table-dark">
        <tr>
          <th scope="col">Date & Time</th>
          <th scope="col">Activities</th>
          <th scope="col">Resources</th>
          <th scope="col">Places</th>
          <th scope="col">Areas</th>
        </tr>
      </thead>
      <tbody></tbody>
    `;

    const tbody = table.querySelector("tbody");

    Object.entries(slots).forEach(([key, slot]) => {
      const [dateStr, timeStr] = key.split("_");

      let formattedDateTime = "Invalid Date";

      if (dateStr && timeStr) {
        const [year, month, day] = dateStr.split("-").map(Number);
        const timeParts = timeStr.match(/^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$/i);

        if (year && month && day && timeParts) {
          let [, hourStr, minuteStr, period] = timeParts;
          let hour = parseInt(hourStr, 10);
          const minute = parseInt(minuteStr || "0", 10);

          if (period.toUpperCase() === "PM" && hour !== 12) hour += 12;
          if (period.toUpperCase() === "AM" && hour === 12) hour = 0;

          const date = new Date(year, month - 1, day, hour, minute);

          formattedDateTime = date.toLocaleString(undefined, {
            weekday: "short",
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
            hour12: true,
          });
        } else {
          console.warn("⚠️ Invalid time format in slot key:", key);
        }
      } else {
        console.warn("⚠️ Invalid slot key format:", key);
      }

      const { resourceList, activityList, placeList, areasList } = processLozenges(
        slot.lozenges,
        areas,
        places,
        tags
      );

      const row = document.createElement("tr");

      // Use Bootstrap text classes for better readability
      row.innerHTML = `
        <td class="align-top">${formattedDateTime}</td>
        <td class="align-top">${activityList.join("<br>")}</td>
        <td class="align-top">${resourceList.join(", ")}</td>
        <td class="align-top">${placeList.join("<br>")}</td>
        <td class="align-top">${areasList.join("<br>")}</td>
      `;
      tbody.appendChild(row);
    });

    return wrapper; // return the responsive wrapper
  }

  function generateSummaryReport() {
    const summary = extractCalendarPlan();
    const areas = window.areas || {};
    const places = window.places || {};
    const tags = window.task_tags || {};

    const summaryTable = buildSummaryTable(summary.slots, areas, places, tags);
    const container = document.getElementById("summary-report");
    container.innerHTML = "";
    container.appendChild(summaryTable);
  }

  function extractCalendarPlan() {
    const calendarPlan = { slots: {} };

    document.querySelectorAll(".slot").forEach(slotDiv => {
      const slotId = slotDiv.dataset.id; // use data-id instead of id
      if (!slotId) return;

      const slotKey = slotId; // already "YYYY-MM-DD_9 AM"
      const availability = parseInt(slotDiv.getAttribute("data-availability")) || 0;

      const lozenges = Array.from(
        slotDiv.querySelectorAll(".lozenge")
      ).map(el => ({
        type: el.dataset.type || null,
        code: el.dataset.code || el.textContent.trim()
      }));

      if (availability > 0 || lozenges.length > 0) {
        calendarPlan.slots[slotKey] = {
          availability,
          lozenges
        };
      }
    });

    return calendarPlan;
  }


  function loadCalendarPlan(plan) {
    const calendarGrid = document.getElementById('calendar-grid');

    // Clear UI

    // Reset calendar data to avoid carrying over entries
    calendarData = {}; // << reset for new calendar

    console.log("📦 Loading plan:", plan);
    if (plan.calendar_plan) plan = plan.calendar_plan;

    if (!plan?.slots) return;

    Object.entries(plan.slots).forEach(([key, slotData]) => {
      const slotDiv = document.querySelector(`.slot[data-id="${key}"]`);
      if (!slotDiv) {
        console.warn("⚠️ Slot not found for key:", key);
        return;
      }

      // Clear the slot before rendering
      slotDiv.innerHTML = "";

      // Re-add time label
      const timeSpan = document.createElement("span");
      timeSpan.className = "slot-time";
      timeSpan.textContent = slotDiv.dataset.time;
      slotDiv.appendChild(timeSpan);

      // Lozenge container
      const lozengeContainer = document.createElement("span");
      lozengeContainer.className = "slot-content"; // or "lozenge-container"
      slotDiv.appendChild(lozengeContainer);

      // Add lozenges
      slotData.lozenges?.forEach(l => {
        const lozEl = createLozengeElement(l);
        lozengeContainer.appendChild(lozEl);
        lozengeContainer.appendChild(document.createTextNode(" "));
      });

      // Store slot data for this calendar
      calendarData[key] = slotData;

      updateSlotAvailability(slotDiv);
      });
      console.log("📦 Loaded plan:", calendarGrid);

  }


  function redrawSlot(slotId, data = {}) {
    const slotDiv = document.querySelector(`.slot[data-id="${slotId}"]`);
    if (!slotDiv) return;

    // Clear existing content
    slotDiv.innerHTML = "";
    // 🛡️ PRESERVE HIGHLIGHT: If this is the active slot, re-apply the class
    if (window.activeSlotId === slotId) {
        slotDiv.classList.add('selected-slot');
    }
    // Re-add time label
    const timeSpan = document.createElement("span");
    timeSpan.className = "slot-time";
    timeSpan.textContent = slotDiv.dataset.time;
    slotDiv.appendChild(timeSpan);

    // Add lozenge container
    const lozengeContainer = document.createElement("span");
    lozengeContainer.className = "slot-content";
    slotDiv.appendChild(lozengeContainer);

    // 🛡️ Bulletproof area mapping with fallbacks to prevent "undefined"
    const areaItems = (data.areas || []).map(r => {
      if (!r) return null;

      let name = "";
      let id = "";

      if (typeof r === 'object') {
        name = r.name || r.nid || r.code || "";
        id = r.nid || r.code || r.name || "";
      } else {
        name = r;
        id = r;
      }

      // If the name or ID is literally "undefined", blank it out
      if (!name || name === "undefined" || name === "null") return null;
      if (!id || id === "undefined" || id === "null") id = name;

      return { type: "area", code: name, id: id };
    }).filter(l => l && l.code && l.code !== "undefined");

    const lozenges = [
      { type: "activity", code: data.activity },
      ...(data.resources || []).map(r => ({ type: "resource", code: r })),
      { type: "place", code: data.place },
      ...areaItems,
    ].filter(l => {
      if (!l || !l.code) return false;
      const strCode = String(l.code).trim();
      return strCode !== "" && strCode !== "undefined" && strCode !== "null" && strCode !== "[object Object]";
    });

    lozenges.forEach(l => {
      const loz = document.createElement("span");
      loz.className = "lozenge";
      loz.dataset.type = l.type;
      loz.dataset.code = l.id || l.code;
      loz.textContent = l.code;
      lozengeContainer.appendChild(loz);
      lozengeContainer.appendChild(document.createTextNode(" "));
    });

    // Store cleaned lozenges back into calendarData
    if (!calendarData[slotId]) calendarData[slotId] = {};
    calendarData[slotId].lozenges = lozenges;
  }


  // --- Slot Modal Handlers ---
  async function handleSaveSlot() {
    if (!currentSlotId) return;

    const activity = document.getElementById("activitySelect").value;
    const place = document.getElementById("placeSelect").value;

    // 🛡️ Grab selected areas, falling back to option text if value is missing/undefined
    const areaSelectEl = document.getElementById("areaSelect");
    const areas = areaSelectEl
      ? Array.from(areaSelectEl.selectedOptions).map(o => {
          let val = o.value;
          // If value is missing, empty, or the literal string "undefined", fall back to text content
          if (!val || val === "undefined" || val === "null") {
            val = o.textContent.trim();
          }
          return {
            nid: val,
            name: o.textContent.trim()
          };
        }).filter(a => a.nid && a.nid !== "undefined")
      : [];

    const resources = Array.from(document.getElementById("resourcesSelect").selectedOptions)
      .map(o => o.value)
      .filter(val => val && val !== "undefined");

    calendarData[currentSlotId] = { activity, place, areas, resources };

    redrawSlot(currentSlotId, calendarData[currentSlotId]);
    console.log(`💾 Slot ${currentSlotId} saved.`, calendarData[currentSlotId]);

    await saveCalendarPlan();
    bootstrap.Modal.getInstance(document.getElementById("slotModal")).hide();
  }

  async function handleClearSlot() {
    if (!currentSlotId) return;

    calendarData[currentSlotId] = {}; // clear memory
    redrawSlot(currentSlotId, {});
    console.log(`🗑️ Slot ${currentSlotId} cleared.`);

    await saveCalendarPlan();
    bootstrap.Modal.getInstance(document.getElementById("slotModal")).hide();
  }





  // Modal logic
  let currentSlotId = null;

  async function saveCalendarPlan() {
    const btn = document.getElementById("save-calendar-btn");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "💾 Saving...";
    }

    // Wrap the in-memory data correctly
    const dataToSave = { calendar_plan: { slots: calendarData } };

    try {
      const response = await fetch(`${API}/current-election`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dataToSave)
      });

      if (!response.ok) throw new Error(`Server responded with ${response.status}`);

      if (btn) btn.textContent = "✅ Saved!";
      console.log("💾 Calendar plan saved:", dataToSave);
    } catch (err) {
      console.error("❌ Failed to save calendar plan:", err);
      if (btn) btn.textContent = "❌ Save Failed";
    } finally {
      if (btn) {
        setTimeout(() => {
          btn.disabled = false;
          btn.textContent = "💾 Save Calendar";
        }, 2000);
      }
    }
  }

  function openSlotModal(slotId) {
      currentSlotId = slotId;
      const slotDiv = document.querySelector(`.slot[data-id="${slotId}"]`);

      // --- 🔴 HIGHLIGHT LOGIC START ---
      // 1. Remove the red outline from any previously highlighted slot
      document.querySelectorAll(".slot.selected-slot").forEach(s => {
          s.classList.remove("selected-slot");
      });

      // 2. Set this slot as the active one and apply the red line class
      if (slotDiv) {
          window.activeSlotId = slotId;
          slotDiv.classList.add("selected-slot");
      }
      // --- 🔴 HIGHLIGHT LOGIC END ---

      // Ensure slot exists in calendarData
      if (!calendarData[slotId]) calendarData[slotId] = {};
      const data = calendarData[slotId]; // Reference, not copy

      // Fill dropdowns
      // 1. Fill ALL dropdowns first so the options exist in the DOM
      fillSelect("activitySelect", window.activities); // <--- Add this (or your activity source)
      fillSelect("placeSelect", window.places);
      fillSelect("areaSelect", window.areas);         // <--- Add this (or your area source)
      fillSelect("resourcesSelect", window.resources);

      // 2. Infer missing fields from DOM lozenges if not already set
      if (!data.resources) data.resources = [];

      const lozenges = Array.from(slotDiv.querySelectorAll(".lozenge"));
      lozenges.forEach(l => {
          const type = l.dataset.type;
          const code = l.dataset.code || l.textContent.trim();

          if (!code || code === "undefined" || code === "null") return;

          if (type === "activity" && !data.activity) {
              data.activity = code;
          } else if (type === "place" && !data.place) {
              data.place = code;
          } else if (type === "area" && !data.area) {
              data.area = code;
          } else if (type === "resource" && !data.resources.includes(code)) {
              data.resources.push(code);
          }
      });

      // 3. Pre-select dropdowns safely now that options exist
      document.getElementById("activitySelect").value = data.activity || "";
      document.getElementById("placeSelect").value = data.place || "";
      document.getElementById("areaSelect").value = data.area || "";

      const resSel = document.getElementById("resourcesSelect");
      Array.from(resSel.options).forEach(opt => {
          opt.selected = data.resources?.includes(opt.value) || false;
      });

      // Show modal
      const modalInstance = new bootstrap.Modal(document.getElementById("slotModal"));
      modalInstance.show();
  }



  function populateResourcesSelect(resourcesSelect, lozenges) {
    // First, clear all selections
    Array.from(resourcesSelect.options).forEach(opt => opt.selected = false);

    // Filter lozenges for type "resource"
    const resourceCodes = lozenges
      .filter(l => l.type === "resource")
      .map(l => l.code);

    // Select matching options
    Array.from(resourcesSelect.options).forEach(opt => {
      // Match by value first
      if (resourceCodes.includes(opt.value)) {
        opt.selected = true;
      } else {
        // Fallback: match by option text (if lozenge stores description instead of code)
        if (resourceCodes.includes(opt.text)) opt.selected = true;
      }
    });
  }



// Expose a function inside the iframe that the parent can call directly:
window.buildAndLoadCalendar = function(plan) {
    if (typeof buildCalendarGrid === "function") {
        buildCalendarGrid("calendar-grid", 45);
    }
    if (typeof populateDropdowns === "function") {
        populateDropdowns();
    }
    if (typeof loadCalendarPlan === "function" && plan) {
        loadCalendarPlan(plan);
    }
};
// ------------------------------
// IN CALENDAR MODAL Add Place button handler
// ------------------------------
document.getElementById("addPlaceBtn")?.addEventListener("click", () => {

    const overlay = document.getElementById("map-overlay");
    const overlayIframe = document.getElementById("overlay-iframe");

    overlayIframe.src = document.getElementById("iframe1").src;
    overlay.style.display = "block";

    overlayIframe.onload = () => {
        console.log("📌 Iframe loaded — sending enableAddPlace");
        overlayIframe.contentWindow.postMessage(
            { type: "enableAddPlace" },
            "*"
        );
    };
});

// ------------------------------
// IN CALENDAR MODAL Save button handler
// ------------------------------
document.getElementById("saveNewPlace")?.addEventListener("click", () => {
    const form = document.getElementById("addPlaceForm");

    // Use the currently selected place data
    const newPlace = selectedPlaceData;
    if (!newPlace) {
        console.error("No place data to save!");
        return;
    }

    // Ensure places dict exists
    if (!window.places) window.places = {};
    window.places[newPlace.prefix] = newPlace;

    // Update dropdown (only prefix)
    fillSelect("placeSelect", window.places);

    // Add marker permanently to FeatureGroup if available
    const markerGroup = window.Featurelayers?.['marker'];
    if (markerGroup && window.pinMarker) {
        markerGroup.addLayer(window.pinMarker);

        // Optionally track by prefix for later reference
        if (!window.permanentMarkers) window.permanentMarkers = {};
        window.permanentMarkers[newPlace.prefix] = window.pinMarker;

        // Clear temporary pointer
        window.pinMarker = null;
    }

    console.log("📌 New place saved:", newPlace);
    console.log("📌 Updated places dict:", window.places);

    // Hide mini-place form and restore overlay/iframe
    form.classList.add("d-none");
    const overlayIframe = document.getElementById("overlay-iframe");
    if (overlayIframe) {
        overlayIframe.classList.remove("dimmed");
        overlayIframe.style.visibility = "hidden";
    }

    // Reset awaitingNewPlace flag
    window.awaitingNewPlace = false;
});

// ------------------------------
// IN CALENDAR MODAL Show add-resource form
// ------------------------------
//
document.getElementById("addResourceBtn")?.addEventListener("click", () => {
    document.getElementById("addResourceForm").classList.remove("d-none");
});

// ------------------------------
// IN CALENDAR MODAL Show save-resource form
// ------------------------------
//
document.getElementById("saveNewResource")?.addEventListener("click", () => {
    const first = newResFirst.value.trim();
    const last  = newResLast.value.trim();
    const email = newResEmail.value.trim();

    if (!first || !last) {
        alert("Firstname and surname required");
        return;
    }

    const code = (first[0] + last).toUpperCase();

    const resourceObj = {
        Firstname: first,
        Surname: last,
        campaignMgremail: email
    };

    // Update global state
    window.resources[code] = resourceObj;

    // ALSO update latestOptions (otherwise UI resets)
    window.latestOptions.resources[code] = resourceObj;

    populateDropdowns();
    updateConstantsUI(window.latestConstants, window.latestOptions);
    populateAllSelects(window.latestOptions, window.latestConstants);


});

// ------------------------------
// IN CALENDAR MODAL Show add-tasktag form
// ------------------------------
//
document.getElementById("addTaskTagBtn")?.addEventListener("click", () => {
    document.getElementById("addTaskTagForm").classList.remove("d-none");
});

// ------------------------------
// IN CALENDAR MODAL Show save-tasktag form
// ------------------------------
//
document.getElementById("saveNewTag")?.addEventListener("click", () => {
    const code  = newTagCode.value.trim();
    const label = newTagLabel.value.trim();

    if (!code || !label) {
        alert("Both code and label required");
        return;
    }

    // Update global
    window.task_tags[code] = label;

    // ALSO update options so updateConstantsUI does not overwrite
    window.latestOptions.task_tags[code] = label;

    // Refresh UI
    populateDropdowns();
    updateConstantsUI(window.latestConstants, window.latestOptions);
    populateAllSelects(window.latestOptions, window.latestConstants);
    addTaskTagForm.classList.add("d-none");
});

/**
 * 2. List Rendering Helper
 * Generates HTML with checkboxes (for bulk) and text (for navigation)
 */
 function renderNodeList(elementId, nodeObjects) {
     const container = document.getElementById(elementId);
     if (!container) return;

     if (!nodeObjects || nodeObjects.length === 0) {
         container.innerHTML = '<div class="none-found" style="padding:10px; color:#888;">No further divisions</div>';
         return;
     }

     container.innerHTML = nodeObjects.map(obj => {
         const path = obj.path;
         const nid = obj.nid;
         const name = obj.name || path.split('/').pop().replace(/_/g, ' ');

         return `
             <div class="nav-item-wrapper" style="display: flex; align-items: center; padding: 5px 0; border-bottom: 1px solid #eee;">
                 <input type="checkbox"
                        class="selectRow"
                        value="${nid}"
                        data-nid="${nid}"
                        onclick="event.stopPropagation();"
                        style="margin-right: 12px; width: 18px; height: 18px; cursor: pointer;">
                 <div class="nav-item"
                      onclick="selectNode('${path}')"
                      style="flex-grow: 1; cursor: pointer; font-size: 14px; color: #333;">
                     ${name}
                 </div>
             </div>`;
     }).join('');
 }

 function attachModalListener() {
     const modal = document.getElementById("modalPopup");
     if (!modal) {
         // Try again in 50ms until it exists
         setTimeout(attachModalListener, 50);
         return;
     }

     // Only attach once
     if (!modal.dataset.listenerAttached) {
         modal.addEventListener("hide.bs.modal", function (e) {
             if (preventModalClose) {
                 console.warn("⛔ Prevented modal from closing — add-place mode active");
                 e.preventDefault();
             }
         });
         modal.dataset.listenerAttached = "true";
     }
 }


 /* ---------------------------------------------------------
  * CALENDAR LOGIN AND CALENDAR BUILD
  * --------------------------------------------------------- */
   const exportBtn = document.getElementById("export-html-btn");
  if (exportBtn) {
    console.log("Initial view set: calendar visible, map hidden");
    exportBtn.addEventListener("click", async () => {
      await saveCalendarPlan();
      const btn = document.getElementById("export-html-btn");
      btn.disabled = true;
      btn.textContent = "🔄 Exporting...";

      try {
        // Create a standalone HTML document

        const htmlContent = createStandaloneHTML();

        // Create a Blob and FormData to send as 'file'
        const blob = new Blob([htmlContent], { type: "text/html" });
        const formData = new FormData();
        formData.append("file", blob, "calendar.html");

        // Upload to development backend
        const response = await fetch("/api/upload-and-protect", {
          method: "POST",
          body: formData
        });

        const result = await response.json();

        if (!response.ok || !result.ok) {
          throw new Error(result.error || "Upload failed");
        }

        btn.textContent = "✅ Exported & Protected";
      } catch (err) {
        console.error("Export failed:", err);
        btn.textContent = "❌ Failed";
      } finally {
        setTimeout(() => {
          btn.textContent = "🔐 Export Protected HTML";
          btn.disabled = false;
        }, 1500);
      }
    });
  }


/* ---------------------------------------------------------
* CALENDAR <-> MAP TOGGLE
* --------------------------------------------------------- */
window.toggleView = function () {
    const mapElement = document.querySelector(".leaflet-container");
    const calendar = document.getElementById("calendar-grid") || document.getElementById("calendar-container");
    const toggleBtn = document.getElementById("backToCalendarBtn");

    if (!mapElement || !calendar) {
        console.warn("⚠️ Map or Calendar container not found for toggleView.");
        return;
    }

    // Explicitly check inline style or use a tracking attribute
    const isCurrentlyCalendar = calendar.style.visibility === "visible";

    if (!isCurrentlyCalendar) {
        // --- Switch TO Calendar ---
        mapElement.style.visibility = "hidden";
        mapElement.style.opacity = "0";
        mapElement.style.pointerEvents = "none";
        mapElement.style.zIndex = "1";

        calendar.style.visibility = "visible";
        calendar.style.opacity = "1";
        calendar.style.pointerEvents = "auto";
        calendar.style.zIndex = "200";

        if (toggleBtn) toggleBtn.textContent = "🧭 View Map";
        console.log("📅 Switched to Calendar view");
    } else {
        // --- Switch TO Map ---
        calendar.style.visibility = "hidden";
        calendar.style.opacity = "0";
        calendar.style.pointerEvents = "none";

        mapElement.style.visibility = "visible";
        mapElement.style.opacity = "1";
        mapElement.style.pointerEvents = "auto";
        mapElement.style.zIndex = "200";

        // Refresh Leaflet map size
        const mapId = mapElement.id;
        if (mapId && window[mapId] && typeof window[mapId].invalidateSize === "function") {
            window[mapId].invalidateSize();
        }

        if (toggleBtn) toggleBtn.textContent = "📅 View Calendar";
        console.log("🗺️ Switched to Map view");
    }
};

 // -----------------------------------------------------
 // NEW PLACE CREATED
 // -----------------------------------------------------
 function fillAddPlaceForm(data) {
     const mapping = {
         prefix: "newPlacePrefix",
         house_number: "newPlaceAddress1",
         road: "newPlaceAddress1",
         suburb: "newPlaceAddress2",
         city: "newPlaceAddress2",
         postcode: "newPlacePostcode",
         url: "newPlaceURL"
     };

     // First, clear form fields
     Object.values(mapping).forEach(id => {
         const el = document.getElementById(id);
         if (el) el.value = "";
     });

     // Fill fields
     for (const key in data) {
         if (!data.hasOwnProperty(key)) continue;
         const fieldId = mapping[key];
         if (!fieldId) continue;

         const el = document.getElementById(fieldId);
         if (!el) continue;

         if (fieldId === "newPlaceAddress1") {
             // Combine house_number + road
             el.value = ((data.house_number || "") + " " + (data.road || "")).trim();
         } else if (fieldId === "newPlaceAddress2") {
             // Combine suburb + city
             el.value = ((data.suburb || "") + " " + (data.city || "")).trim();
         } else {
             el.value = data[key] || "";
         }
     }

     // Save lat/lng in dataset
     const form = document.getElementById("addPlaceForm");
     form.dataset.lat = data.lat;
     form.dataset.lng = data.lng;

     form.classList.remove("d-none");
 }

 function activateMapForAddPlace() {
     const iframe = document.getElementById("iframe1");
     const modal = document.getElementById("slot-modal");
     const calendarScroll = document.getElementById("calendar-scroll");

     addPlaceActive = true;         // your existing state variable
     preventModalClose = true;      // stops accidental closing

     iframe.classList.add("map-active");

     // Dim everything else but keep modal visually visible
     if (modal) {
         modal.classList.add("dimmed");
     }

     if (calendarScroll) {
         calendarScroll.classList.add("dimmed");
     }

     console.log("🗺️ Map activated for Add Place.");
 }



 function deactivateMapAfterPlaceSelected() {
   const modal = document.getElementById("slot-modal");
     const calendarScroll = document.getElementById("calendar-scroll");

     iframe.classList.remove("map-active");

     if (modal) {
         modal.classList.remove("dimmed");
     }

     if (calendarScroll) {
         calendarScroll.classList.remove("dimmed");
     }

     addPlaceActive = false;
     preventModalClose = false;

     console.log("📅 Map overlay deactivated; modal restored.");
 }

 function openAddResourceForm() {
 const id = prompt("Enter new resource code (unique ID like R101):");
 if (!id) return;

 const Firstname = prompt("Enter first name:");
 const Surname = prompt("Enter surname:");
 const campaignMgremail = prompt("Enter campaign manager email (optional):") || "";
 const addResourceForm = document.getElementById("addResourceForm");

 if (!Firstname || !Surname) return alert("Firstname and Surname are required");

 // Create resource object
 window.resources[id] = {
     Firstname,
     Surname,
     campaignMgremail
 };

 addResourceForm.classList.add("d-none");

console.log("Added new resource:", window.resources[id]);
}

function openAddTaskTagForm() {
   const tag = prompt("Enter new task tag code (e.g., L5):");
   if (!tag) return;

   if (window.task_tags[tag]) {
       return alert("This task tag already exists!");
   }

   const description = prompt("Enter task tag description:");
   if (!description) return;

   window.task_tags[tag] = description;

   console.log("Added new task tag:", tag, description);

   updateConstantsUI(window.latestConstants, window.latestOptions);
   populateAllSelects(window.latestOptions, window.latestConstants);
   alert("Task tag added!");
}


async function getCalendarUpdate(API) {
    if (!window.currentElectionName) return;

    try {
        const election = window.currentElectionName;
        console.log("📦 Fetching election:", election);

        const response = await fetch(`${API}/current-election?election=${encodeURIComponent(election)}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        console.log("📦 Backend response:", data);

         window.plan = data.calendar_plan;

         updateConstantsUI(data.constants, data.options);
         populateAllSelects(data.options, data.constants);
         console.log("📩 update calendar_plan::", plan);
//               console.log("🔀 update places on DOM relaod :", places);
//               console.log("🔀 update resources on DOM relaod :", resources);
//               console.log("🔀 update areas on DOM relaod :", areas);
//               console.log("🔀 update task_tags on DOM relaod :", task_tags);

       window.plan = data.constants?.calendar_plan;
        if (!window.plan || !window.plan.slots) {
            console.warn("⚠️ No slots found in calendar_plan");
            return;
        }

        loadCalendarPlan(window.plan);
        console.log("✅ Calendar plan loaded into UI");

    } catch (err) {
        console.error("🚨 Error fetching calendar plan:", err);
    }
}
  /* ---------- Sync Helpers for Single Select ---------- */
window.selectedArea = null;
window.selectedTask = null;

function syncAreaSelect() {
const sel = document.getElementById('areaSelect');
if (!sel) return;
sel.innerHTML = '';
if (!window.selectedArea) return;
sel.appendChild(new Option(window.selectedArea, window.selectedArea, true, true));
sel.value = window.selectedArea;
}

function syncTaskSelect() {
const sel = document.getElementById('activitySelect');
if (!sel) return;
sel.innerHTML = '';
if (!window.selectedTask) return;
sel.appendChild(new Option(window.selectedTask, window.selectedTask, true, true));
sel.value = window.selectedTask;
}


  /* ---------- Return selected areas ---------- */

  window.getSelectedAreas = function() {

      return [...window.selectedAreas].map(name => ({
          name: name
      }));
  };

  window.getSelectedTasks = function() {

      return [...window.selectedTasks].map(name => ({
          name: name
      }));
  };


  /* ---------- Recursive Tree Selector ---------- */
  window.renderTreeSelector = function (tree, options = {}) {
      const {
          containerId,
          emptyMessage = 'No items available',
          accordionId,
          allLabel = name => `All of ${name}`,
          createButton
      } = options;

      const container = document.getElementById(containerId);
      if (!container) return;

      container.innerHTML = '';

      if (
          !tree ||
          typeof tree !== 'object' ||
          Object.keys(tree).length === 0
      ) {
          container.innerHTML =
              `<div class="small text-muted p-2">${emptyMessage}</div>`;
          return;
      }

      const acc = document.createElement('div');
      acc.className = 'accordion';
      acc.id = accordionId;

      let idCounter = 0;

      function renderLevel(node, parentElement, path = [], depth = 0) {
          if (!node || typeof node !== 'object') return;

          Object.entries(node).forEach(([name, children]) => {
              const currentPath = [...path, name];

              const hasChildren =
                  children &&
                  typeof children === 'object' &&
                  Object.keys(children).length > 0;

              // IMPORTANT: no \(...\)
              const uniqueId = `${accordionId}-${idCounter++}`;

              // -------------------------------------------------
              // TOP LEVEL
              // -------------------------------------------------
              if (depth === 0) {
                  const item = document.createElement('div');
                  item.className =
                      'accordion-item border-0 mb-1';

                  item.innerHTML = `
                      <h2 class="accordion-header">
                          <button
                              class="accordion-button collapsed py-2 shadow-none"
                              type="button"
                              data-bs-toggle="collapse"
                              data-bs-target="#${uniqueId}"
                              aria-expanded="false">
                              ${name}
                          </button>
                      </h2>

                      <div
                          id="${uniqueId}"
                          class="accordion-collapse collapse">

                          <div class="accordion-body p-0"></div>
                      </div>
                  `;

                  const body =
                      item.querySelector('.accordion-body');

                  // Select entire top-level branch
                (
                      body,
                      name,
                      allLabel(name),
                      'fw-semibold'
                  );

                  if (hasChildren) {
                      renderLevel(
                          children,
                          body,
                          currentPath,
                          depth + 1
                      );
                  }

                  parentElement.appendChild(item);
                  return;
              }

              // -------------------------------------------------
              // NESTED LEVEL
              // -------------------------------------------------
              const wrapper = document.createElement('div');
              wrapper.className = 'border-0';

              if (hasChildren) {
                  const header = document.createElement('button');

                  header.type = 'button';
                  header.className =
                      'btn btn-sm w-100 text-start py-2 shadow-none';

                  header.style.paddingLeft =
                      `${1 + depth * 1.25}rem`;

                  header.setAttribute(
                      'data-bs-toggle',
                      'collapse'
                  );

                  header.setAttribute(
                      'data-bs-target',
                      `#${uniqueId}`
                  );

                  header.setAttribute(
                      'aria-expanded',
                      'false'
                  );

                  header.textContent = `▸ ${name}`;

                  const collapse = document.createElement('div');
                  collapse.id = uniqueId;
                  collapse.className = 'collapse';

                  const list = document.createElement('div');
                  list.className =
                      'list-group list-group-flush';

                  // Select entire branch
                  createButton(
                      list,
                      name,
                      allLabel(name),
                      ''
                  );

                  // Recursively render children
                  renderLevel(
                      children,
                      list,
                      currentPath,
                      depth + 1
                  );

                  collapse.appendChild(list);

                  wrapper.appendChild(header);
                  wrapper.appendChild(collapse);

              } else {
                  // -------------------------------------------------
                  // LEAF
                  // -------------------------------------------------
                  createButton(
                      wrapper,
                      name,
                      name,
                      ''
                  );
              }

              parentElement.appendChild(wrapper);
          });
      }

      renderLevel(tree, acc);

      container.appendChild(acc);
  };

  function createAreaButton(
    list,
    areaName,
    displayName,
    indentClass = '',
    selectedKey = 'selectedArea'
) {
    const button = document.createElement('button');

    button.type = 'button';
    button.className =
        `list-group-item list-group-item-action small ${indentClass}`;

    button.textContent = displayName;
    button.dataset.name = areaName;

    if (window[selectedKey] === areaName) {
        button.classList.add('active');
    }

    button.addEventListener('click', function () {
        const accordion = list.closest('.accordion');

        if (accordion) {
            accordion
                .querySelectorAll('.list-group-item')
                .forEach(btn => btn.classList.remove('active'));
        }

        window[selectedKey] = areaName;

        button.classList.add('active');

        console.log('Area selected:', areaName);

        syncAreaSelect();
    });

    list.appendChild(button);
}

function createTaskButton(
  list,
  taskCode,
  displayName,
  indentClass = '',
  selectedKey = 'selectedTask'
) {
  const button = document.createElement('button');

  button.type = 'button';
  button.className =
      `list-group-item list-group-item-action small ${indentClass}`;

  button.textContent = displayName;
  button.dataset.code = taskCode;

  if (window[selectedKey] === taskCode) {
      button.classList.add('active');
  }

  button.addEventListener('click', function () {
      const accordion = list.closest('.accordion');

      if (accordion) {
          accordion
              .querySelectorAll('.list-group-item')
              .forEach(btn => btn.classList.remove('active'));
      }

      window[selectedKey] = taskCode;

      button.classList.add('active');

      console.log('Task selected:', taskCode);

      syncTaskSelect();
  });

  list.appendChild(button);
}

// Example: If clicking a button triggers or displays the area tree
document.getElementById("someAreaButtonId")?.addEventListener("click", () => {
    // Assuming window.areaTree is already populated or fetched from your map data
    if (window.areaTree) {
        console.log('Rendering area tree...');
        renderTreeSelector(window.areaTree, {
            containerId: 'areaAccordionContainer',
            accordionId: 'areaSelectAccordion',
            emptyMessage: 'No areas available for this map',
            allLabel: name => `All of ${name}`,
            createButton: createAreaButton
        });
    }
});

// Example: Same for the task tree button
document.getElementById("someTaskButtonId")?.addEventListener("click", () => {
    if (window.taskTree) {
        console.log('Rendering task tree...');
        renderTreeSelector(window.taskTree, {
            containerId: 'taskAccordionContainer',
            accordionId: 'taskSelectAccordion',
            emptyMessage: 'No task types available for this map',
            allLabel: name => `All of ${name}`,
            createButton: createTaskButton
        });
    }
});




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
     // 1. Safely retrieve the BAKED_DATA array across window contexts
     var parentWindow = window.parent || window;
     const iframe = document.getElementById('iframe1');
     const iframeWin = iframe?.contentWindow;

     // Fallback order: Iframe data -> Parent/Main window data -> empty array
     const eventLog = (iframeWin && iframeWin.BAKED_DATA) || parentWindow.BAKED_DATA || window.BAKED_DATA || [];

     // 2. Filter down strictly to events that are explicitly NOT synced
     // Treating undefined/missing 'synced' properties as un-synced (false)
     const unsynced = eventLog.filter(e => e.synced !== true);

     if (unsynced.length === 0) {
         console.log("ℹ️ No un-synced local changes found.");
         return Promise.resolve(true);
     }

     console.log(`🚀 Batch uploading ${unsynced.length} un-synced changes to server...`);

     // 3. POST the unsynced changes wrapped in an 'events' object to match the backend expectations
     return fetch('/upload_data', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ events: unsynced })
     })
     .then(res => {
         if (!res.ok) throw new Error("Network collection upload synchronization failed");

         // 4. Mark successfully uploaded elements as synced in the active memory array
         unsynced.forEach(e => {
             e.synced = true;
         });

         // 5. Sync state to LocalStorage for safety
         localStorage.setItem('CANVASS_BAKED_DATA', JSON.stringify(eventLog));
         console.log("🚀 Sync complete! Remote server updated and local cache synchronized.");

         // Clear warning indicators or toggle save button elements if present
         var deployBtn = document.getElementById('deploy-btn') || parentWindow.document.getElementById('deploy-btn');
         if (deployBtn) deployBtn.disabled = true;

         return true;
     })
     .catch(err => {
         console.error("❌ Failed to push batch payload modifications to database container:", err);
         return false;
     });
 };

 (function startMapCatcher() {

     // Helper function to safely execute the sync call
     const runBackendSync = () => {
         const parentWindow = window.parent || window;
         const targetSync = parentWindow.syncBackend || window.syncBackend;
         if (typeof targetSync === 'function') {
             console.log("💾 [DISMISS SYNC] Closing trigger detected. Syncing to backend...");
             targetSync().then(success => {
                 if (success) {
                     console.log("✅ Auto-sync successful on dismissal.");
                 } else {
                     console.warn("⚠️ Auto-sync failed on dismissal.");
                 }
             }).catch(err => {
                 console.error("❌ Error running syncBackend:", err);
             });
         }
     };

     // -------------------------------------------------------------
     // GLOBAL BUBBLED EVENT LISTENER (Folium/Dynamic Friendly)
     // -------------------------------------------------------------
     // Since Folium injects the elements dynamically on click, we intercept
     // the Bootstrap event at the document root level where it always bubbles up.

     document.addEventListener('hidden.bs.modal', async (event) => {
        if (event.target.id !== 'slotModal')
            return;
        console.log("🎯 Modal closed. Syncing...");
        if (typeof window.syncBackend === "function") {
            await window.syncBackend();
        }
        });

     // Global console manual test hook
     window.triggerManualDebugClose = () => {
      const modalEl = document.getElementById("slotModal");
      if (!modalEl) {
          console.warn("No slotModal found.");
          return;
      }
      const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
      modal.hide();
      };

     // -------------------------------------------------------------
     // LEAFLET MAP REFRESH FINDER
     // -------------------------------------------------------------
     const findMap = () => {
         for (const key in window) {
             if (key.startsWith('map_') && window.L && window[key] instanceof window.L.Map) {
                 window.fmap = window[key];
                 window.fmap.invalidateSize();
                 window.MAP_READY = true;
                 hydrateMapOnce();
                 if (window.__pendingRender) window.__pendingRender = null;
                 return true;
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

     // 1. Gather unique region identifiers
     const uniqueRegionIds = new Set();
     currentData.forEach(ev => {
         if (ev && ev.region) {
             uniqueRegionIds.add(String(ev.region).trim().toUpperCase());
         }
     });

     console.log(`🔄 [PENDING RENDER] Executing batch update for unique regions:`, Array.from(uniqueRegionIds));

     // 2. Extract valid election layers (which explicitly includes 'VI' already)
     const activeLayers = Object.keys(window.task_tags || {});

     // 3. Batch process matches
     uniqueRegionIds.forEach(region_id => {
         if (!region_id || region_id === "UNDEFINED") return;

         activeLayers.forEach(layerTag => {
             window.plotTaskProgress(region_id, layerTag, 'walk');
         });
     });
 };

 window.iframeSwitchElection = function (electionName, data) {
     // 1. UI: Update title inside the iframe
     const title = document.getElementById("calendar-title");
     if (title) title.textContent = `${electionName} Campaigns Calendar`;

     // 2. Update Iframe Global State & Options
     window.latestConstants = data.constants;
     window.latestOptions = data.options;

     if (typeof updateConstantsUI === "function") updateConstantsUI(data.constants, data.options);
     if (typeof populateAllSelects === "function") populateAllSelects(data.options, data.constants);

     window.plan = data.constants?.calendar_plan;
     const mapfiles = data.constants?.mapfiles || [];
     const lastMapFile = mapfiles.slice(-1)[0];

     // 3. Inject context switch event into BAKED_DATA
     window.BAKED_DATA = window.BAKED_DATA || [];
     window.BAKED_DATA.push({
         "type": "context_switch",
         "election": String(electionName).toUpperCase().trim(),
         "ts": Date.now()
     });

     // 4. Load Calendar inside the iframe
     if (window.plan && window.plan.slots) {
         if (typeof buildCalendarGrid === "function") buildCalendarGrid("calendar-grid", 45);
         if (typeof populateDropdowns === "function") populateDropdowns();
         if (typeof loadCalendarPlan === "function") loadCalendarPlan(window.plan);
     }

     // 5. Load Map inside the iframe
     if (lastMapFile) {
         const correctedPath = lastMapFile.includes('.')
             ? lastMapFile
             : `${lastMapFile}.html`;

         // If you have a local iframe map changer or helper, invoke it here:
         if (typeof changeIframeSrc === "function") {
             changeIframeSrc(`/thru/${correctedPath}`);
         } else {
             window.location.href = `/thru/${correctedPath}`;
         }
     }
 };

 //  message listener when the parent uses postMessage instead of direct function call
 window.addEventListener("message", (event) => {
     if (event.data && event.data.type === "iframeSwitchElection") {
         // 1. Store it globally inside the iframe so it's always accessible
         window.currentElectionName = event.data.electionName;

         // 2. Pass it to your handler function
         if (typeof window.iframeSwitchElection === "function") {
             window.iframeSwitchElection(event.data.electionName, event.data.data);
         }
     }
 });


 window.MAP_READY = false;
 window.__HYDRATED = false;

 function hydrateMapOnce() {
     // 🛡️ BREAKOUT 1: If it's already done, stop.
     if (window.__HYDRATED) return;

     // 🛡️ BREAKOUT 2: Check if our dynamic async task tags have arrived from the backend yet!
     // If window.task_tags only has 'VI' or is empty, the server payload hasn't landed. Hold off.
     const tagRegistry = window.task_tags || {};
     const tagCodes = Object.keys(tagRegistry);

     if (tagCodes.length <= 1) {
         console.log("⏳ [Hydration] Postponing map paint. Waiting for async task_tags from backend...");
         return;
     }

     const currentData = getBakedData();
     if (!Array.isArray(currentData) || currentData.length === 0) return;

     window.__HYDRATED = true;
     console.log(`🎯 [HYDRATION RUNNING] Painting layers for active tags: [${tagCodes.join(', ')}]`);

     const uniqueRegions = [
         ...new Set(
             currentData
                 .map(e => e && e.region ? String(e.region).trim().toUpperCase() : null)
                 .filter(Boolean)
         )
     ];

     for (const region_id of uniqueRegions) {
         if (!region_id || region_id === "UNDEFINED") continue;
         for (const code of tagCodes) {
             window.plotTaskProgress(region_id, code, 'walk');
         }
     }
 }




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
        row.style.backgroundColor = "#28a745"; // Green (Completed)
        row.style.color = "#ffffff";
    } else if (count > 0) {
        row.style.backgroundColor = "#ffcc00"; // Yellow (In Progress)
        row.style.color = "#000000";
    } else {
        row.style.backgroundColor = "";        // Reset Default Dark background
        row.style.color = "#ffffff";
    }

    // Force nested elements to respect inherit styling rules
    row.querySelectorAll('td, b, i, span').forEach(el => {
        el.style.color = "inherit";
    });
};


function deriveState(events) {
    const state = {};
    for (const e of events) {
        if (!e.uiScope || !e.region || !e.street || !e.house) continue;

        state[e.uiScope] ??= {};
        state[e.uiScope][e.region] ??= {};
        state[e.uiScope][e.region][e.street] ??= {};
        state[e.uiScope][e.region][e.street][e.house] ??= { tags: {}, votes: 0, vi: "" };

        if (e.type === 'tag') {
            state[e.uiScope][e.region][e.street][e.house].tags[e.code] = e.value;
        } else if (e.type === 'vi') {
            state[e.uiScope][e.region][e.street][e.house].votes = parseInt(e.votes || 0, 10);
            state[e.uiScope][e.region][e.street][e.house].vi = e.vi || "";
        }
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

    // --- FIX: Extract structural context variables so they exist in scope ---
    var doc = row.ownerDocument;
    var region = row.getAttribute('data-region');
    var street = row.getAttribute('data-street');
    var house = unitSel.value;
    var uiScope = row.getAttribute('data-scope');

    if (!region || !street || !house) return;

    // --- FIX: Use your VI non-zero vote sum algorithm for streetWeight ---
    var streetWeight = 0;
    var streetRows = doc.querySelectorAll(`.canvass-row[data-region="${region}"][data-street="${street}"]`);

    streetRows.forEach(function(r) {
        var rBtn = r.querySelector('.vote-btn') || r.querySelector('.vote-count-btn');
        var rCount = parseInt(rBtn?.getAttribute('data-count') || rBtn?.dataset.count || '0');

        // Use the look-ahead value we just cycled for the row being actively clicked
        if (r === row) {
            rCount = count;
        }

        if (rCount > 0) {
            streetWeight++;
        }
    });

    // 2. Calculate global Region Weight (Absolute total house capacities in the entire region)
    var regionWeight = 0;
    var countedStreetsInRegion = new Set();
    var allRowsInRegion = doc.querySelectorAll(`.canvass-row[data-region="${region}"]`);

    allRowsInRegion.forEach(function(r) {
        var sKey = r.getAttribute('data-street');
        if (!sKey || countedStreetsInRegion.has(sKey)) return;
        countedStreetsInRegion.add(sKey);

        var sSel = r.querySelector('.unit-selector');
        var sRows = doc.querySelectorAll(`.canvass-row[data-region="${region}"][data-street="${sKey}"]`);
        regionWeight += sSel ? sSel.options.length : sRows.length;
    });

    // Attach exclusively to parent master storage container
    var parentWindow = window.parent || window;
    if (!parentWindow.BAKED_DATA) parentWindow.BAKED_DATA = [];

    // =========================================================================
    // DISCOVER CURRENT ELECTION CONTEXT FOR DATA STAMPING (MODULARIZED)
    // =========================================================================
    var currentElection = window.getCurrentElectionContext(parentWindow.BAKED_DATA, doc);

    // Append the logged entry completely tagged with its election timeline target
    parentWindow.BAKED_DATA.push({
        type: 'vi',
        election: currentElection, // <-- STAMPED CONTEXT
        uiScope: uiScope,
        region: region,
        street: street,
        house: house,
        vi: viSel.value,
        votes: count,
        streetWeight: streetWeight,
        regionWeight: regionWeight,
        ts: Date.now(),
        synced: false
    });

    // --- ADDED: Auto-Save & Map Retrigger Loops ---
    if (typeof parentWindow.saveBakedData === 'function') {
        parentWindow.saveBakedData(parentWindow.BAKED_DATA);
    }
    if (typeof parentWindow.plotTaskProgress === 'function') {
        parentWindow.plotTaskProgress(region, 'VI', uiScope);
    } else if (typeof plotTaskProgress === 'function') {
        plotTaskProgress(region, 'VI', uiScope);
    }
    if (window.updateMarkerStatus) {
        window.updateMarkerStatus(street);
    }

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
    const house = sel?.value;
    if (!region || !street || !house) return;

    // =========================================================================
    // 1. ACTIVE WEIGHT ESTIMATION
    // =========================================================================
    let streetWeight = 0;

    // CRITICAL FIX: If toggling to 'n' (inactive), weight should be explicitly 0
    // to signal deletion/untagging to the mapping engine.
    if (newValue === 'y') {
        const streetRows = doc.querySelectorAll(`.canvass-row[data-region="${region}"][data-street="${street}"]`);

        streetRows.forEach(r => {
            const targetSpan = r.querySelector(`.tag-toggle[data-code="${code}"]`);
            let isTagActiveOnRow = targetSpan ? (targetSpan.getAttribute('data-value') === 'y') : false;

            // Use the newly clicked state look-ahead for the row being actively modified
            if (r === row) {
                isTagActiveOnRow = true;
            }

            if (isTagActiveOnRow) {
                streetWeight++;
            }
        });
    } else {
        streetWeight = 0; // Explicitly zero out the weight on untag
    }

    // 2. Calculate global Region Weight
    let regionWeight = 0;
    const countedStreetsInRegion = new Set();
    const allRowsInRegion = doc.querySelectorAll(`.canvass-row[data-region="${region}"]`);

    allRowsInRegion.forEach(r => {
        const sKey = r.getAttribute('data-street');
        if (!sKey || countedStreetsInRegion.has(sKey)) return;
        countedStreetsInRegion.add(sKey);

        const sSel = r.querySelector('.unit-selector');
        if (sSel) {
            regionWeight += Array.from(sSel.options).reduce((sum, opt) => {
                return sum + parseInt(opt.getAttribute('data-max') || 1, 10);
            }, 0);
        } else {
            const sRows = doc.querySelectorAll(`.canvass-row[data-region="${region}"][data-street="${sKey}"]`);
            regionWeight += sRows.length;
        }
    });

    // =========================================================================
    // 3. STATE SYNCHRONIZATION AND DOM WRITING
    // =========================================================================
    span.classList.toggle('tag-active', newValue === 'y');
    span.classList.toggle('tag-inactive', newValue === 'n');
    span.innerText = newValue;

    // Set attribute so updateTagToggles and our look-ahead loop read it accurately
    span.setAttribute('data-value', newValue);

    // Write logs straight up to global parent window memory space
    var parentWindow = window.parent || window;
    parentWindow.BAKED_DATA ||= [];

    // DISCOVER CURRENT ELECTION CONTEXT FOR DATA STAMPING
    const currentElection = window.getCurrentElectionContext(parentWindow.BAKED_DATA, doc);

    parentWindow.BAKED_DATA.push({
        type: 'tag',
        election: currentElection,
        ts: Date.now(),
        uiScope: uiScope,
        region: region,
        street: street,
        house: house,
        tag_code: code,
        value: newValue,
        streetWeight: streetWeight,
        regionWeight: regionWeight,
        synced: false
    });

    // --- Auto-Save execution ---
    if (typeof parentWindow.saveBakedData === 'function') {
        parentWindow.saveBakedData(parentWindow.BAKED_DATA);
    }

    // Keep map progression charting synced
    // FIX: Trigger BOTH the specific code and the fallback 'VI' (Voting Intention)
    // code in case the map's ghost layer only listens to overall 'VI' progress.
    const plotProgress = (reg, cd, scope) => {
        if (typeof parentWindow.plotTaskProgress === 'function') {
            parentWindow.plotTaskProgress(reg, cd, scope);
        } else if (typeof plotTaskProgress === 'function') {
            plotTaskProgress(reg, cd, scope);
        }
    };

    plotProgress(region, code, uiScope);
    if (code !== 'VI') {
        plotProgress(region, 'VI', uiScope); // Fallback to update global coverage
    }

    // Toggle save button state to remind them there are un-deployed adjustments
    var deployBtn = parentWindow.document.getElementById('deploy-btn') || document.getElementById('deploy-btn');
    if (deployBtn) deployBtn.disabled = false;
};

window.updateTagToggles = function(selector, uiScope = 'walk') {
    const row = selector.closest('.canvass-row') || selector.closest('tr');
    if (!row) return;

    const region = row.dataset.region;
    const street = row.dataset.street;
    const house = selector.value; // The currently selected unit (e.g. house number)

    // 1. EXTRACT ELECTION CONTEXT
    const parentWindow = window.parent || window;
    const events = parentWindow.BAKED_DATA || [];
    const currentElection = window.getCurrentElectionContext(events, row.ownerDocument);

    // 2. DISCOVER BASELINE DATA FOR SELECTED HOUSE
    // Note: Since tags are only server-rendered for the FIRST unit, we default
    // any other unit's baseline to 'n' (inactive) unless updated by BAKED_DATA logs.
    const firstOption = row.querySelector('.unit-selector option');
    const isFirstUnitSelected = firstOption && (firstOption.value === house);

    const finalComputedTags = {};

    row.querySelectorAll('.tag-toggle').forEach(span => {
        const code = span.dataset.code ? span.dataset.code.toUpperCase() : '';
        if (!code) return;

        // If the user selected the first unit, read the backend's server-rendered state
        // from the HTML attributes. Otherwise, other units start fresh ('n')
        if (isFirstUnitSelected) {
            finalComputedTags[code] = (span.getAttribute('data-value') || 'n').toLowerCase();
        } else {
            finalComputedTags[code] = 'n';
        }
    });

    // 3. APPLY BAKED_DATA OVERRIDES FOR THE SELECTED UNIT CHRONOLOGICALLY
    const relevantEvents = events.filter(e =>
        e.type === 'tag' &&
        e.election === currentElection &&
        e.uiScope === uiScope &&
        e.region === region &&
        e.street === street &&
        e.house === house
    );

    relevantEvents.forEach(e => {
        if (e.code) {
            finalComputedTags[e.code.toUpperCase()] = String(e.value).toLowerCase();
        }
    });

    // 4. PRECISION UI UPDATE & SYNC
    row.querySelectorAll('.tag-toggle').forEach(span => {
        const code = span.dataset.code ? span.dataset.code.toUpperCase() : '';
        if (!code) return;

        const val = finalComputedTags[code] === 'y' ? 'y' : 'n';

        // Update classes and internal tracker values so subsequent clicks read accurately
        span.classList.toggle('tag-active', val === 'y');
        span.classList.toggle('tag-inactive', val !== 'y');
        span.innerText = val;
        span.setAttribute('data-value', val); // Maintain state parity inside DOM
    });
};

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

    // =========================================================================
    // DISCOVER CURRENT ELECTION CONTEXT FOR REPLAY FILTERING (MODULARIZED)
    // =========================================================================
    const currentElection = window.getCurrentElectionContext(localLogs, doc);

    console.log(`🔄 [POPUP REPLAY] Scanning local ledger for Region: ${currentRegion} [Scope: ${currentScope}] [Election: ${currentElection || 'NONE'}]`);

    // 3. Scan ledger to paint overrides onto the HTML view
    localLogs.forEach(ev => {
        if (!ev) return;

        // Guard: Verify event belongs to this election timeline, scope, and region
        if (ev.type !== 'context_switch' && ev.election !== currentElection) return;
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
                // FIX: Stamped payload properties use 'ev.vi', not 'ev.value'
                viSel.value = ev.vi || '';
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

/**
 * Resolves the active election timeline context from event logs or the DOM fallback.
 * @param {Array} events - The array of events (BAKED_DATA).
 * @param {Document} [customDoc] - Optional document context for tab fallbacks.
 * @returns {string} The active election code in uppercase, or empty string.
 */
window.getCurrentElectionContext = function(events, customDoc) {
    const logList = events || window.BAKED_DATA || [];

    // 1. Scan backward for a context switch boundary token
    for (let k = logList.length - 1; k >= 0; k--) {
        if (logList[k] && logList[k].type === "context_switch") {
            return String(logList[k].election).toUpperCase();
        }
    }

    // 2. Safety Fallback: Query active DOM tabs if array token isn't present
    const doc = customDoc || document;
    const activeTab = doc.querySelector(".election-tab.active") ||
                      (window.parent !== window ? window.parent.document.querySelector(".election-tab.active") : null);

    if (activeTab) {
        return (activeTab.dataset.election || activeTab.textContent.trim()).toUpperCase();
    }

    return "";
};

window.updateMarkerStatus = function(region_id, uiScope = 'walk') {

    if (!region_id) return;

    // -------------------------------------------------
    // 1️⃣ DERIVE STATE FROM EVENTS (CONTEXT FILTERED)
    // -------------------------------------------------
    const events = window.BAKED_DATA || [];

    // Call our brand-new modular context look-up helper!
    const currentElection = window.getCurrentElectionContext(events);

    const state = {};
    // Inside updateMarkerStatus:
    for (const e of events) {
        if (e.type !== 'context_switch' && e.election !== currentElection) continue;
        if (e.uiScope !== uiScope) continue;
        if (e.region !== region_id) continue;
        if (e.type !== 'vi') continue; // 🌟 FIX: Only parse 'vi' events for vote-weight tracking

        state[e.street] ??= {};
        state[e.street][e.house] ??= { votes: 0 };

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

/**
 * 2. Visual Model Heatmap Engine
 * Aligned to search both parent page or local iframe environments
 * and targets '.vote-btn' elements.
 */
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

     // Find Document Context (Parent Dashboard vs Nested IFrame Container)
     const doc = document.getElementById('iframe1')?.contentWindow?.document || document;
     const rows = doc.querySelectorAll(`.canvass-row[data-region="${cleanId}"]`);

     let totalHouses = 0;
     let completedHouses = 0;

     // -----------------------------------------------------------------
     // CONDITION A: Canvas View is OPEN (Check DOM Elements)
     // -----------------------------------------------------------------
     if (rows.length > 0) {
         console.log("📊 UI active. Calculating opacity from live canvas elements...");

         if (isViTarget) {
             rows.forEach(r => {
                 totalHouses++; // Every row represents a unique unit capacity target

                 // Matches restored .vote-btn class name
                 const voteBtn = r.querySelector('.vote-btn') || r.querySelector('.vote-count-btn');
                 const voteCount = parseInt(voteBtn?.getAttribute('data-count') || voteBtn?.dataset?.count || '0');

                 if (voteCount > 0) {
                     completedHouses++;
                 }
             });
         } else {
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
                     if (r.querySelector(`.tag-toggle[data-code="${targetTag}"].tag-active`)) {
                         streetIsActive = true;
                     }
                 });

                 if (streetIsActive) {
                     completedHouses += streetWeight;
                 }
             });
         }
     }
     // -----------------------------------------------------------------
     // CONDITION B: Canvas View is CLOSED (Read Local Cache Logs)
     // -----------------------------------------------------------------
     else {
         console.log("💾 UI closed. Calculating opacity via baked region weights...");

         const eventLog = window.BAKED_DATA || parent.BAKED_DATA || [];

         // 🌟 FIX 1: Resolve current election context so past election data doesn't skew stats
         const currentElection = window.getCurrentElectionContext(eventLog, doc);

         let bakedRegionCeiling = 0;
         const streetWeightRegistry = {};
         const streetActiveHouses = {};

         eventLog.forEach(ev => {
             if (!ev) return;
             // 🌟 FIX 2: Skip context switches or mismatches from other elections
             if (ev.type === 'context_switch' || ev.election !== currentElection) return;
             if (ev.uiScope !== uiScope) return;
             if (String(ev.region).trim().toUpperCase() !== cleanId) return;

             const street = ev.street;
             const house = ev.house;

             if (ev.streetWeight) streetWeightRegistry[street] = ev.streetWeight;
             if (ev.regionWeight) bakedRegionCeiling = ev.regionWeight;

             if (!streetActiveHouses[street]) {
                 streetActiveHouses[street] = new Set();
             }

             // 🌟 FIX 3: Process the normalized tag changes
             if (ev.type === 'tag') {
                 if (String(ev.code).toUpperCase() === String(targetTag).toUpperCase()) {
                     if (ev.value === 'y') {
                         streetActiveHouses[street].add(house);
                     } else if (ev.value === 'n') {
                         streetActiveHouses[street].delete(house);
                     }
                 }
             }
             // 🌟 FIX 4: Aligned 'vi' parameter structures
             else if (isViTarget && ev.type === 'vi' && ev.votes !== undefined) {
                 const voteValue = parseInt(ev.votes || '0', 10);
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

     const finalOpacity = totalHouses > 0 ? 0.8 * (completedHouses / totalHouses) : 0;

     console.log("📐 OPACITY ANALYSIS METRICS:", {
         region: cleanId,
         totalHouses,
         completedHouses,
         calculatedOpacity: finalOpacity
     });

     // -------------------------------------------------
     // LAYER TARGET GROUP DISCOVERY
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
     // APPLY OPACITY / UPDATE EXISTING GHOST
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
     // GEOMETRY STRUCTURAL LOOKUP
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

     const poly = Leaflet.geoJSON(geometry, {
         pane: 'overlayPane',
         style: {
             color: "transparent",
             fillColor: targetTag === 'VI' ? "#800080" : "#333",
             fillOpacity: finalOpacity,
             interactive: false
         }
     });

     poly.is_ghost = true;
     poly.ghost_id = ghostId;

     targetGroup.addLayer(poly);

     console.log(`✨ Ghost successfully registered to group: ${ghostId}`);
     console.groupEnd();
 };
/**
 * 3. Initialize State Sync on Row Load
 * Synchronizes select-option values and vote UI elements.
 */
window.initializeStreetRowState = function(sel, scope) {
    var parentWindow = window.parent || window;
    var row = sel.closest('.canvass-row');
    if (!row) return;

    if (parentWindow.BAKED_DATA && Array.isArray(parentWindow.BAKED_DATA)) {
        var currentUnit = sel.value;
        var streetName = row.getAttribute('data-street');
        var regionId = row.getAttribute('data-region');

        for (var i = parentWindow.BAKED_DATA.length - 1; i >= 0; i--) {
            var log = parentWindow.BAKED_DATA[i];
            if (log.type === 'vi' &&
                String(log.uiScope) === String(scope) &&
                String(log.region) === String(regionId) &&
                String(log.street) === String(streetName) &&
                String(log.house) === String(currentUnit)) {

                var viSel = row.querySelector('.vi-selector');
                if (viSel) {
                    viSel.value = log.vi;
                }

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

    if (typeof parentWindow.loadHouseData === 'function') parentWindow.loadHouseData(sel);
    if (typeof parentWindow.refreshDropdownColors === 'function') parentWindow.refreshDropdownColors(sel);
    if (typeof parentWindow.updateTagToggles === 'function') parentWindow.updateTagToggles(sel, scope);

    if (typeof parentWindow.refreshRowVoteBadge === 'function') {
        parentWindow.refreshRowVoteBadge(row);
    }
};

/**
 * 4. Active Row Badge Repaint Handlers
 */
window.refreshRowVoteBadge = function(rowElement){
    if (!rowElement) return;
    var unitSel = rowElement.querySelector('.unit-selector');
    var viSel = rowElement.querySelector('.vi-selector');
    var btn = rowElement.querySelector('.vote-btn');
    if (!unitSel || !viSel || !btn) return;

    var currentUnit = unitSel.value;
    var currentVi = viSel.value ? viSel.value.toUpperCase() : "";

    var selectedOpt = unitSel.options[unitSel.selectedIndex];
    var maxVotes = selectedOpt ? (selectedOpt.getAttribute('data-max') || 1) : 1;

    var streetName = rowElement.getAttribute('data-street');
    var scope = rowElement.getAttribute('data-scope') || 'walk';
    var regionId = rowElement.getAttribute('data-region');

    var count = 0;
    var foundInFreshLogs = false;

    var bakedLogs = window.BAKED_DATA || parent.BAKED_DATA || [];
    if (Array.isArray(bakedLogs)) {
        for (var i = bakedLogs.length - 1; i >= 0; i--) {
            var log = bakedLogs[i];

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

    if (!foundInFreshLogs) {
        var activeVotesDb = {};
        try {
            activeVotesDb = JSON.parse(rowElement.getAttribute('data-active-votes-db') || '{}');
        } catch(e) {
            console.error("Failed to parse row data-active-votes-db", e);
        }

        if (activeVotesDb[currentUnit]) {
            for (var key in activeVotesDb[currentUnit]) {
                if (key.toUpperCase() === currentVi) {
                    count = activeVotesDb[currentUnit][key];
                    break;
                }
            }
        }
    }

    btn.setAttribute('data-count', count);
    btn.setAttribute('data-max', maxVotes);
    btn.innerText = count + '/' + maxVotes;
};

/**
 * 5. Dropdown Navigation State Synchronizer
 */
 window.handleUnitChangeVIUpdate = function(unitSel) {
     var parentWindow = window.parent || window;
     var row = unitSel.closest('.canvass-row') || unitSel.closest('tr');
     if (!row) return;

     var selectedUnit = unitSel.value;
     var viSel = row.querySelector('.vi-selector');
     var voteBtn = row.querySelector('.vote-btn');
     if (!viSel || !voteBtn) return;

     var regionId = row.getAttribute('data-region');
     var streetName = row.getAttribute('data-street');
     var uiScope = row.getAttribute('data-scope') || 'walk';

     var chosenViCode = "";
     var currentVotes = 0;
     var maxVotes = parseInt(unitSel.options[unitSel.selectedIndex].getAttribute('data-max')) || 1;

     var eventLog = parentWindow.BAKED_DATA || window.BAKED_DATA || [];
     var currentElection = window.getCurrentElectionContext(eventLog, row.ownerDocument);

     // Scan backwards through the flat ledger for the latest matching VI record
     for (var k = eventLog.length - 1; k >= 0; k--) {
         var log = eventLog[k];
         if (
             log.type === 'vi' &&
             log.election === currentElection &&
             String(log.uiScope) === String(uiScope) &&
             String(log.region) === String(regionId) &&
             String(log.street) === String(streetName) &&
             String(log.house) === String(selectedUnit)
         ) {
             chosenViCode = log.vi || "";
             currentVotes = parseInt(log.votes) || 0;
             break;
         }
     }

     // Fallback to dataset baseline values if no local modifications exist in flat logs
     if (!chosenViCode) {
         var activeVotesDb = {};
         try {
             activeVotesDb = JSON.parse(row.getAttribute('data-active-votes-db') || '{}');
         } catch (e) {
             console.error("Failed to parse row data-active-votes-db", e);
         }

         if (activeVotesDb[selectedUnit]) {
             // Find the key with non-zero votes, or default to the first key
             var keys = Object.keys(activeVotesDb[selectedUnit]);
             if (keys.length > 0) {
                 chosenViCode = keys[0];
                 currentVotes = activeVotesDb[selectedUnit][chosenViCode] || 0;
             }
         }
     }

     // Update UI DOM states
     if (chosenViCode) {
         viSel.value = chosenViCode;
     } else {
         viSel.selectedIndex = 0; // Reset to default VI code option
     }

     voteBtn.setAttribute('data-count', currentVotes);
     voteBtn.setAttribute('data-max', maxVotes);
     voteBtn.innerText = currentVotes + '/' + maxVotes;
 };

/**
 * 6. Visual Theme Engine Renderer
 */
window.applyRowColorStyles = function(row) {
    var parentWindow = window.parent || window;
    var unitSel = row.querySelector('.unit-selector');
    var viSel = row.querySelector('.vi-selector');
    var voteBtn = row.querySelector('.vote-btn');

    if (!unitSel || !viSel || !voteBtn) {
        return;
    }

    if (!unitSel.hasAttribute('data-styles-bound')) {
        unitSel.setAttribute('data-styles-bound', 'true');
        unitSel.addEventListener('change', function() {
            setTimeout(function() {
                window.applyRowColorStyles(row);
            }, 10);
        });
    }

    var regionId = row.getAttribute('data-region');
    var streetName = row.getAttribute('data-street');

    var vcoPalette = {
        "S": "#DC241F", "C": "#0087DC", "LD": "#FAA61A", "G": "#6AB023",
        "R": "#00BFFF", "I": "#4B0082", "PC": "#990033", "SD": "#E65C00",
        "O": "#8B4513", "Z": "#7F8C8D", "W": "#DCDCDC", "X": "#34495E"
    };

    var viDots = {
        'S': '🔴', 'C': '🔵', 'LD': '🟡', 'G': '🟢', 'R': '🔵',
        'O': '🟤', 'I': '🟣', 'PC': '🟤', 'SD': '🟠', 'Z': '⚪',
        'W': '⚪', 'X': '⚫'
    };

    var houseViMap = {};
    var processedHouses = new Set();

    var eventLog = parentWindow.BAKED_DATA || window.BAKED_DATA || [];
    var targetRegionToken = String(regionId || '').toLowerCase().replace(/[^a-z0-9]/g, '').trim();
    var targetStreetToken = String(streetName || '').toLowerCase().replace(/[^a-z0-9]/g, '').trim();

    for (var i = eventLog.length - 1; i >= 0; i--) {
        var ev = eventLog[i];
        if (!ev) continue;

        var evType = String(ev.type || ev.model || '').toLowerCase().trim();
        if (evType.indexOf('vi') !== -1) {

            var evRegionToken = String(ev.region || ev.regionId || '').toLowerCase().replace(/[^a-z0-9]/g, '').trim();
            var evStreetToken = String(ev.street || ev.streetName || '').toLowerCase().replace(/[^a-z0-9]/g, '').trim();

            if (evRegionToken === targetRegionToken && evStreetToken === targetStreetToken) {
                var houseKey = String(ev.house || ev.unit || '').trim();

                if (houseKey && !processedHouses.has(houseKey)) {
                    processedHouses.add(houseKey);

                    var rawVi = ev.vi ? String(ev.vi).toUpperCase().trim() : '';

                    if (rawVi === '' || rawVi === 'UNCANVASSED' || rawVi === 'U') {
                        houseViMap[houseKey] = 'U';
                    } else {
                        houseViMap[houseKey] = rawVi;
                    }
                }
            }
        }
    }

    var rawDb = row.getAttribute('data-active-votes-db');
    var parsedDbObject = {};

    if (rawDb) {
        try {
            parsedDbObject = JSON.parse(rawDb);
            Object.keys(parsedDbObject).forEach(function(hKey) {
                if (processedHouses.has(hKey)) {
                    return;
                }

                var houseVotes = parsedDbObject[hKey] || {};
                var codes = Object.keys(houseVotes);
                if (codes.length > 0) {
                    var highestCode = codes.reduce(function(a, b) {
                        return (parseInt(houseVotes[a] || 0) >= parseInt(houseVotes[b] || 0)) ? a : b;
                    });
                    var normCode = String(highestCode).toUpperCase().trim();
                    if (normCode && normCode !== '{}' && normCode !== 'U' && normCode !== 'UNCANVASSED') {
                        houseViMap[hKey] = normCode;
                    }
                }
            });
        } catch (e) {}
    }

    Object.keys(houseViMap).forEach(function(hKey) {
        var currentViValue = houseViMap[hKey];
        if (currentViValue && currentViValue !== 'U') {
            if (!parsedDbObject[hKey]) parsedDbObject[hKey] = {};
            parsedDbObject[hKey] = {};
            parsedDbObject[hKey][currentViValue] = 1;
        } else if (currentViValue === 'U' && parsedDbObject[hKey]) {
            parsedDbObject[hKey] = {};
        }
    });

    row.setAttribute('data-active-votes-db', JSON.stringify(parsedDbObject));

    Array.from(unitSel.options).forEach(function(option) {
        var cleanName = option.value || option.text;
        cleanName = cleanName.replace(/[\uD83C-\uDBFF][\uDC00-\uDFFF]|\s\s🟢|\s\s🔴|\s\s🔵|\s\s🟡|\s\s🟣|\s\s🟤|\s\s⚪|\s\s⚫/g, '').trim();

        var assignedVi = houseViMap[option.value];
        var hasMatch = !!(assignedVi && assignedVi !== 'U' && vcoPalette[assignedVi]);

        if (hasMatch) {
            option.text = cleanName + "  " + viDots[assignedVi];
            option.style.color = vcoPalette[assignedVi];
            option.style.backgroundColor = "#ffffff";
            option.style.fontWeight = 'bold';
        } else {
            option.text = cleanName;
            option.style.color = '';
            option.style.backgroundColor = '';
            option.style.fontWeight = '';
        }
    });

    var activeHouseNumber = unitSel.value;
    var activeHouseVi = houseViMap[activeHouseNumber];

    if (activeHouseVi && activeHouseVi !== 'U' && vcoPalette[activeHouseVi]) {
        var targetBgColor = vcoPalette[activeHouseVi];

        row.style.backgroundColor = targetBgColor;
        row.style.color = "#ffffff";
        row.style.fontWeight = '500';

        unitSel.style.color = "#ffffff";
        unitSel.style.fontWeight = '500';
    } else {
        row.style.backgroundColor = '';
        row.style.color = '';
        row.style.fontWeight = '';

        unitSel.style.color = '';
        unitSel.style.fontWeight = '';
    }

    try {
        var renderEvent = new Event('render');
        unitSel.dispatchEvent(renderEvent);
    } catch(e) {}
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
              tagsResponse: tagsValue,
              synced: false
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
    PC: "darkred", SD: "orange", Z: "#006064",
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

    var regionId = row.getAttribute('data-region');
    var streetName = row.getAttribute('data-street');
    var uiScope = row.getAttribute('data-scope') || 'walk';
    var selectedHouse = unitSel.value;

    var finalVotes = parseInt(voteBtn.getAttribute('data-count')) || 0;
    var currentSelectionValue = selectElement.value ? selectElement.value.trim() : '';

    // Calculate database weights...
    var eventLog = parentWindow.BAKED_DATA || [];
    var doc = row.ownerDocument;
    var streetWeight = 0;
    var regionWeight = 0;
    var activeHousesOnStreet = new Set();

    eventLog.forEach(function(ev) {
        if (ev.type === 'vi' && ev.region === regionId && ev.street === streetName) {
            if ((parseInt(ev.votes) || 0) > 0) activeHousesOnStreet.add(ev.house);
            else activeHousesOnStreet.delete(ev.house);
        }
    });
    if (finalVotes > 0) activeHousesOnStreet.add(selectedHouse);
    else activeHousesOnStreet.delete(selectedHouse);
    streetWeight = activeHousesOnStreet.size;

    var countedStreetsInRegion = new Set();
    doc.querySelectorAll(`.canvass-row[data-region="${regionId}"]`).forEach(function(r) {
        var sKey = r.getAttribute('data-street');
        if (!sKey || countedStreetsInRegion.has(sKey)) return;
        countedStreetsInRegion.add(sKey);
        var sSel = r.querySelector('.unit-selector');
        regionWeight += sSel ? sSel.options.length : doc.querySelectorAll(`.canvass-row[data-region="${regionId}"][data-street="${sKey}"]`).length;
    });

    // Log the interaction explicitly
    parentWindow.BAKED_DATA.push({
        type: 'vi',
        uiScope: uiScope,
        region: regionId,
        street: streetName,
        house: selectedHouse,
        vi: currentSelectionValue,
        votes: finalVotes,
        streetWeight: streetWeight,
        regionWeight: regionWeight,
        ts: Date.now(),
        synced: false
    });

    // Run styling logic safely
    window.applyRowColorStyles(row);

    // Run downstream storage & synchronization tasks
    if (typeof parentWindow.saveBakedData === 'function') parentWindow.saveBakedData(parentWindow.BAKED_DATA);
    if (typeof parentWindow.plotTaskProgress === 'function') parentWindow.plotTaskProgress(regionId, 'VI', uiScope);
    if (window.updateMarkerStatus) window.updateMarkerStatus(streetName);
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
      // Fixed: corrected to use standard ${} interpolation
      tooltipContent = `${resourceInfo?.Firstname || ''}${resourceInfo?.Surname || ''}`.trim();
      console.log("Resource Tooltips", tooltipContent);
 } else if (loz.type === "place") {
     const placeInfo = window.places?.[loz.code];
     tooltipContent = placeInfo?.tooltip;
     console.log("Place Tooltip ", loz.code, placeInfo);
     // Safely guard these debug logs against undefined hydration states
     console.log("placeDetails keys:", window.places ? Object.keys(window.places) : "Not loaded yet");
     console.log("placeDetails values:", window.places);
 } else if (loz.type === "tag") {
       const tagInfo = window.task_tags?.[loz.code];
       tooltipContent = tagInfo;
       console.log("Task tag Tooltip ",loz.code,tagInfo);
       console.log("tagDetails values:", Object.values(window.task_tags));

     };


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

// --- Inside your Iframe Script ---

window.addEventListener("message", (event) => {
    const data = event.data;

    // Check if the message is instructing us to load a calendar plan
    if (data && data.type === "loadCalendarPlan") {
        console.log("📩 Iframe received loadCalendarPlan message:", data.plan);

        if (typeof window.buildAndLoadCalendar === "function") {
            window.buildAndLoadCalendar(data.plan);
        } else {
            console.warn("⚠️ buildAndLoadCalendar function is not defined in the iframe scope.");
        }
    }
});

document.addEventListener("DOMContentLoaded", () => {
    console.log("🔥 Iframe DOMContentloaded — initializing calendar & modal environment");

    console.log("🔀 places on DOM reload :", window.places);
    console.log("🔀 resources on DOM reload :", window.resources);
    console.log("🔀 task_tags on DOM reload :", window.task_tags);

    let selectedPlaceData = null; // Store data from the map
    let preventModalClose = false;
    let addPlaceActive = false;


    // 2. Modal & View Switch Buttons
    const switchToMapBtn = document.getElementById("switch-tomap-btn");
    const saveCalendarBtn = document.getElementById("save-calendar-btn");
    const generateSummaryBtn = document.getElementById("generate-summary-btn");
    const saveSlotBtn = document.getElementById("saveSlotBtn");
    const clearSlotBtn = document.getElementById("clearSlotBtn");

    switchToMapBtn?.addEventListener("click", () => {
        window.toggleView?.();
    });

    saveCalendarBtn?.addEventListener("click", saveCalendarPlan);
    generateSummaryBtn?.addEventListener("click", generateSummaryReport);
    saveSlotBtn?.addEventListener("click", handleSaveSlot);
    clearSlotBtn?.addEventListener("click", handleClearSlot);

    window.activeSlotId = null;

    // 3. Baked Data Setup
    window.BAKED_DATA = window.BAKED_DATA || (parent && parent.BAKED_DATA) || [];
    var fmap;

    // 4. Build Calendar UI & Dropdowns ONCE
    console.log("📅 Building calendar UI & dropdowns...");
    buildCalendarGrid("calendar-grid", 45);
    populateDropdowns();
    console.log("📅 Calendar UI ready.");

    // 5. Load Plan Data
    if (typeof getCalendarUpdate === "function") {
        getCalendarUpdate(window.API);
        console.log("📅 Calendar data loaded.");
    }

    // 6. Calendar Grid Delegated Slot Clicks
    const calendarGrid = document.getElementById("calendar-grid");
    if (calendarGrid) {
        calendarGrid.addEventListener("click", (e) => {
            const slotDiv = e.target.closest(".slot");
            if (slotDiv) {
                const slotId = slotDiv.dataset.id;
                if (slotId && typeof openSlotModal === "function") {
                    openSlotModal(slotId);
                }
            }
        });
    }

    // 7. Initial Calendar State (Hidden by default)
    const calendar = document.getElementById("calendar");
    if (calendar) {
        calendar.style.visibility = "hidden";
        calendar.style.opacity = "0";
        calendar.style.pointerEvents = "none";
        calendar.style.zIndex = "1";
    }
    // 8. Initialize Modals
        if (typeof attachModalListener === "function") {
            attachModalListener();
        }

        window.loggedIn = true;
        window.calendar = document.getElementById("calendar");
        window.loginBtn = document.getElementById("loginBtn");
        window.passwordInput = document.getElementById("password");
        window.loginMessage = document.getElementById("loginMessage");

        // 1. Find the toggle button in the DOM
        window.toggleBtn = document.getElementById("backToCalendarBtn") || document.getElementById("switch-tomap-btn");

        // 2. Set its initial button text
        if (toggleBtn) {
            toggleBtn.textContent = "📅 View Calendar";

            // 3. Bind the click listener EXACTLY ONCE cleanly
            toggleBtn.addEventListener("click", async () => {
                await window.toggleView?.();
            });
        } else {
            console.warn("⚠️ Toggle button not found in the DOM.");
        }
    });
