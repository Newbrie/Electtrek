


  function createStandaloneHTML() {
    const doctype = "<!DOCTYPE html>\n";

    // ✅ Clone once
    const clone = document.documentElement.cloneNode(true);

    // ✅ Remove duplicate calendar content
    const calendar = clone.querySelector("#calendar-grid");
    if (calendar) {
      calendar.innerHTML = "";
    }

    // ✅ Serialize the edited clone
    let htmlString = doctype + clone.outerHTML;

    // ✅ Replace placeholder with final API URL
    const FINAL_API_URL = DEVURLS['prod'];
    htmlString = htmlString.replace(/__REPLACE_WITH_API_URL__/g, FINAL_API_URL);

    return htmlString;
  }


  document.getElementById("export-html-btn").addEventListener("click", async () => {
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

  // Format hours nicely
  function formatHour(hour) {
    const ampm = hour >= 12 ? "PM" : "AM";
    const h = (hour % 12) || 12;
    return `${h} ${ampm}`;
  }

  // Build 45-day x 2-hour grid
  function buildCalendarGrid(containerId, daysToShow = 45) {
    const container = document.getElementById(containerId);
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
          placeList.push(`Area: ${loz.code} – ${areaInfo.details.join(", ")}`);
        } else {
          placeList.push(`Area: ${loz.code}`);
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

  return { resourceList, activityList, placeList };
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

    const { resourceList, activityList, placeList } = processLozenges(
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

  // Re-add time label
  const timeSpan = document.createElement("span");
  timeSpan.className = "slot-time";
  timeSpan.textContent = slotDiv.dataset.time;
  slotDiv.appendChild(timeSpan);

  // Add lozenge container
  const lozengeContainer = document.createElement("span");
  lozengeContainer.className = "slot-content";
  slotDiv.appendChild(lozengeContainer);

  // Build lozenges from data
  const lozenges = [
    { type: "activity", code: data.activity },
    ...(data.resources || []).map(r => ({ type: "resource", code: r })),
    { type: "place", code: data.place },
    ...(data.areas || []).map(r => ({ type: "area", code: r })),
  ].filter(l => l.code);

  lozenges.forEach(l => {
    const loz = document.createElement("span");
    loz.className = "lozenge";
    loz.dataset.type = l.type;
    loz.dataset.code = l.code;
    loz.textContent = l.code;
    lozengeContainer.appendChild(loz);
    lozengeContainer.appendChild(document.createTextNode(" "));
  });

  // Store lozenges for summary/report
  calendarData[slotId].lozenges = lozenges;
}


// --- Slot Modal Handlers ---
async function handleSaveSlot() {
  if (!currentSlotId) return;

  const activity = document.getElementById("activitySelect").value;
  const place = document.getElementById("placeSelect").value;
//  const area = document.getElementById("areaSelect").value;
  const areas = Array.from(document.getElementById("areaSelect").selectedOptions).map(o => o.value);
  const resources = Array.from(document.getElementById("resourcesSelect").selectedOptions).map(o => o.value);

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


    // Ensure slot exists in calendarData
    if (!calendarData[slotId]) calendarData[slotId] = {};
    const data = calendarData[slotId]; // Reference, not copy

    // 🔽 INJECT AREA ACCORDION HERE
    populateAreaAccordion(window.areas);

    // Fill dropdowns
    fillSelect("activitySelect", window.task_tags);
    fillSelect("resourcesSelect", window.resources);
    fillSelect("placeSelect", window.places);
    console.log("💾 filled resources:", window.resources);
    // Infer from lozenges if data is empty
    if (!data.activity && !data.place && !data.area && (!data.resources || !data.resources.length)) {
        data.resources = [];
        const lozenges = Array.from(slotDiv.querySelectorAll(".lozenge"));
        lozenges.forEach(l => {
            switch (l.dataset.type) {
                case "activity": data.activity = l.dataset.code; break;
                case "place": data.place = l.dataset.code; break;
                case "area": data.area = l.dataset.code; break;
                case "resource": data.resources.push(l.dataset.code); break;
            }
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
