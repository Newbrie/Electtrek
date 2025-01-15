

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
  }

}

// Close the dropdown if the user clicks outside of it
window.onclick = function(event) {
if (!event.target.matches('.dropbtn')) {
  var dropdowns = document.getElementsByClassName("dropdown-content");
  var i;
  for (i = 0; i < dropdowns.length; i++) {
    var openDropdown = dropdowns[i];
    if (openDropdown.classList.contains('show')) {
      openDropdown.classList.remove('show');
    }
  }
}
}

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

function email_csv(csv, filename) {
  var csvFile;
  var downloadLink;
  csvFile = new Blob([csv], {type: "text/csv"});
  FileLink = document.createElement("a");
  FileLink.download = filename;
  FileLink.href = window.URL.createObjectURL(csvFile);
  document.body.appendChild(FileLink);

};


function openForm() {
    document.getElementById("myForm").style.display = "block";
  }

function closeForm() {
    document.getElementById("myForm").style.display = "none";
  }

function export_table_to_csv(html, filename) {
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
          }
  csv.push(row.join(","));
  }
  // Download CSV
  download_csv(csv.join("\n"), filename);
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
          }
  csv.push(row.join(","));
  }
  // Download CSV
  email_csv(csv.join("\n"), email);
};

document.querySelector("button.SAVE").addEventListener("click", function () {
  var html = document.querySelector("table tr").outerHTML;
  var filename = "{{ walk_name }}-data.csv";
  export_table_to_csv(html, filename);
  });

document.querySelector("button.SEND").addEventListener("click", function () {
  var html = document.querySelector("table").outerHTML;
  var filename = "{{ walk_name }}-data.csv";
  var base_email = "surrey@reformuk.com"
  email_html_to_base(html, base_email);
  });
