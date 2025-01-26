
// addEventListener support for IE8
function bindEvent(element, eventName, eventHandler) {
   if (element.addEventListener){
       element.addEventListener(eventName, eventHandler, false);
   } else if (element.attachEvent) {
       element.attachEvent('on' + eventName, eventHandler);
   };
};
// Listen to message from child window
var results = document.getElementById('results');
var iframeEl = document.getElementsByName('iframe1');
alert(results.id);
alert(iframeEl.name);
  bindEvent(window, 'message', function (e) {
    results.innerHTML = "<blink>"+e.data+"</blink>";
    alert(results.innerHTML);
});


//document.querySelector("button.SAVE").addEventListener("click", function () {
//  var html = document.querySelector("table").outerHTML;
//  var filename = "{{ walkname }}-data.csv";
//  export_table_to_csv(html, filename);
//  });
