/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

var moveDown = function (msg, area, type) {
    window.parent.postMessage(`Drilling down to ${type} level within ${area}`, '*');

    const ul = parent.document.getElementById("logwin");
    if (ul) ul.scrollTop = ul.scrollHeight;
    window.location.assign(msg);
//    alert("Submitting to: " + msg);

};


var moveUp = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage("Moving up to "+ area + " "+ type+ " level ", '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = ul.scrollHeight;

      };
var showMore = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage("Showing the "+type+ " level within "+ area, '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = ul.scrollHeight;
      };

      /* When the user clicks on the button,
      toggle between hiding and showing the dropdown content */



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

    function fetchTableData(tableName) {
      fetch(`/get_table/${tableName}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin"
      })
      .then(response => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
      })
      .then(data => {
          if (!Array.isArray(data) || data.length < 3) {
              console.error("Invalid or incomplete data:", data);
              return;
          }

          const columnHeaders = data[0];
          const rows = data[1];
          const title = data[2];

          tabtitle.innerHTML = title;
          tabhead.innerHTML = "";
          tabbody.innerHTML = "";

          const headRow = document.createElement("tr");
          const checkboxHeader = document.createElement("th");
          checkboxHeader.textContent = "?";
          headRow.appendChild(checkboxHeader);

          columnHeaders.forEach(header => {
              const th = document.createElement("th");
              th.textContent = header.toUpperCase();
              headRow.appendChild(th);
          });

          tabhead.appendChild(headRow);

          rows.forEach(record => {
              const row = document.createElement("tr");
              const checkboxCell = document.createElement("td");
              const checkbox = document.createElement("input");
              checkbox.type = "checkbox";
              checkbox.name = "selectRow[]";
              checkbox.classList.add("selectRow");
              checkboxCell.appendChild(checkbox);
              row.appendChild(checkboxCell);

              columnHeaders.forEach(header => {
                  const cell = document.createElement("td");
                  const value = record[header] !== undefined ? record[header] : "";
                  cell.innerHTML = value;

                  if (header === yourparty.value) {
                      const color = VCO[yourparty.value] || "inherit";
                      cell.style.backgroundColor = color;
                  }

                  row.appendChild(cell);
              });

              tabbody.appendChild(row);
          });
      })
      .catch(error => console.error("Table fetch error:", error));
    }


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
      console.log("Data received:", data);

      if (!Array.isArray(data) || data.length < 3) {
          console.error("Invalid or incomplete data:", data);
          return;
      }

      if (!tabhead || !tabbody || !tabtitle) {
          console.error("tabhead or tabbody not found");
          return;
      }


      const columnHeaders = data[0];  // First element contains ordered column names
      const rows = data[1];            // Second element contains data rows
      const title = typeof data[2] === 'number' ? data[2].toString() : data[2]; // third element contains title
      // Clear previous content
      tabtitle.innerHTML = "";
      tabhead.innerHTML = "";
      tabbody.innerHTML = "";

      // Build table head row

      const headRow = document.createElement("tr");
      const checkboxHeader = document.createElement("th");

      tabtitle.innerHTML = title;
      checkboxHeader.textContent = "?";
      headRow.appendChild(checkboxHeader);

      columnHeaders.forEach(header => {
          const th = document.createElement("th");
          th.textContent = header.toUpperCase();
          headRow.appendChild(th);
      });

      tabhead.appendChild(headRow);
      console.log("🗺️ received json table details:", tabtitle+tabhead+tabbody);
      // Build table body
      rows.forEach(record => {
          const row = document.createElement("tr");

          // Checkbox cell
          const checkboxCell = document.createElement("td");
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.name = "selectRow[]";
          checkbox.classList.add("selectRow");
          checkboxCell.appendChild(checkbox);
          row.appendChild(checkboxCell);

          // Data cells
          columnHeaders.forEach(header => {
            const cell = document.createElement("td");
            const value = record[header] !== undefined ? record[header] : "";
            cell.innerHTML = value;

            // Highlight the column whose name matches `yourparty`
            if (header === yourparty.value) {
                const color = VCO[yourparty.value] || "inherit";
                cell.style.backgroundColor = color;
            }

            row.appendChild(cell);
            });
            tabbody.appendChild(row);
         });
     })
     .catch(error => console.error("Elector Table Fetch error:", error));

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
        window.parent.postMessage("Refreshing summary data set ", '*');
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
