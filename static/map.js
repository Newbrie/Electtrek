/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

var moveDown = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage("Drilling down to "+type+ " set within "+ area, '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = ul.scrollHeight;
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
      window.parent.postMessage("Showing the "+type+ " set within "+ area, '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = ul.scrollHeight;
      };

      /* When the user clicks on the button,
      toggle between hiding and showing the dropdown content */


  async function getVIData(path) {
      let table = document.getElementById("canvass-table");
      let inputs = table.querySelectorAll("td.VI"); // Select all VI fields
      let data = [];
      alert(inputs);
      inputs.forEach(input => {
          let row = input.closest("tr"); // Get the closest row
          let electorID = row.cells[1].innerText.trim(); // Assuming 'ENOP' is in the second column
          let viValue = row.cells[7].innerText.trim(); // Get input value

          if (viValue) {
          data.push({
              electorID: electorID,
              viResponse: viValue
            });
          };
      });

      console.log("Collected VI Data:", data);

      // Send data to server
      const selnode = path;

      alert("fetching:"+selnode);
      fetch(selnode, {  // Use full URL to ensure correct routing
          method: "POST",
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
              alert("Loading: " + data.file);
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


  function email_csv(csv, filename) {
    var csvFile;
    var downloadLink;
    csvFile = new Blob([csv], {type: "text/csv"});
    FileLink = document.createElement("a");
    FileLink.download = filename;
    FileLink.href = window.URL.createObjectURL(csvFile);
    document.body.appendChild(FileLink);
    alert("Nede to invoke javascript email client"+ FileLink)
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
  	var rows = document.querySelectorAll("table tr");
    var headcols = ["PD","ENOP","ElectorName","VI","Notes"];
    var head = []

    for (var i = 0; i < rows.length; i++) {
    if (i==0){
      for (var j = 0; j < headcols.length; j++){
          head.push(headcols[j]) };
      csv.push(head.join(","));
      }
    else if (i==1){
      }
    else {
      var row = [], cols = rows[i].querySelectorAll("td");
          if (cols.length > 6) {
              var pick = [0,1,2,7,8];
              for (var j = 0; j < cols.length; j++){
                if (pick.includes(j)){
                  row.push(cols[j].innerText.replaceAll(",", ""));
                };
              };
          };
      csv.push(row.join(","));
      };
    };
      // Download CSV
      download_csv(csv.join("\n"), filename);
  };

  var layerUpdate = function (path) {
    // Send a message to the parent
        var filename = path.split('/').pop().replace("DATA.html","DATA.csv");
        alert(filename);
        var html = document.querySelector("#canvass-table").outerHTML;
        alert("html"+html);
        export_table_to_csv(html, filename);
        console.log(filename);
        var htmlpath = path.replace("DATA.csv","PRINT.html");
        getVIData(htmlpath);
        window.parent.postMessage("Refreshing summary data set ", '*');
        };

  function inputVI(VI) {
    let x = VI.value.toUpperCase();
    const VID = {"R" : "Reform","C" : "Conservative","S" : "Labour","LD" :"LibDem","G" :"Green","I" :"Independent","PC" : "Plaid Cymru","SD" : "SDP","Z" : "Maybe","W" :  "Wont Vote", "X" :  "Won't Say"}

    const codes = Object.keys(VID);
    if (codes.includes(x)) {
  //  let y = "<span> <input type=\"text\" onchange=\"copyinput(this)\" maclength=\"2\" size=\"2\" name=\"example-unique-id-A3078.0\" id=\"example-unique-id-E3078.0\" placeholder=\"{0}\"></span>".format(x);
      VI.style.color = 'lightgray';
  //    VI.innerHTML = x;
      VI.parentElement.parentElement.innerText = x;
      }
    else {
      VI.style.color = 'darkgray';
  //    VI.innerHTML = x;
      VI.parentElement.parentElement.innerText = "??";
    }
    };

  function inputNS(NS) {
    let x = NS.value;
    NS.style.color = 'lightgray';
    NS.innerHTML = x;
    NS.parentElement.parentElement.innerText = x;

    };


  //document.querySelector("button.SAVE").addEventListener("click", function () {
  //  var html = document.querySelector("table").outerHTML;
  //  var filename = "{{ walkname }}-data.csv";
  //  export_table_to_csv(html, filename);
  //  });
