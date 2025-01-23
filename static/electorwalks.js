/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */
function myFunction() {
  var select = document.getElementById("dropCluster");
  var options = ["1", "2", "3", "4", "5"];

  // Optional: Clear all existing options first:
  select.innerHTML = "";
  // Populate list with options:
  for(var i = 0; i < options.length; i++) {
      var opt = options[i];
      select.innerHTML += "<option value=\"" + opt + "\">" + opt + "</option>";
  };

};

// Close the dropdown if the user clicks outside of it
window.onclick = function(event) {
if (!event.target.matches('.dropbtn')) {
  var dropdowns = document.getElementsByClassName("dropdown-content");
  var i;
  for (i = 0; i < dropdowns.length; i++) {
    var openDropdown = dropdowns[i];
    if (openDropdown.classList.contains('show')) {
      openDropdown.classList.remove('show');
    };
  };
};
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

document.getElementById('save-btn').addEventListener('click', function() {
  var filename = document.getElementById("save-btn").getAttribute("data1");
  var html = document.querySelector("#canvass-table").outerHTML;
	export_table_to_csv(html, filename);
  console.log(filename);
});

function inputVI(VI) {
  let x = VI.value.toUpperCase();
  const codes = ["C","R","S","LD","G","I","M","X","W"];
  if (codes.includes(x)) {
//  let y = "<span> <input type=\"text\" onchange=\"copyinput(this)\" maclength=\"2\" size=\"2\" name=\"example-unique-id-A3078.0\" id=\"example-unique-id-E3078.0\" placeholder=\"{0}\"></span>".format(x);
    VI.style.color = 'lightgray';
    VI.innerHTML = x;
    VI.parentElement.parentElement.innerText = x;
    };
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
