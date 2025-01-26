
// addEventListener support for IE8
function bindEvent(blink, element, eventName, eventHandler) {
   if (element.addEventListener){
       element.addEventListener(eventName, eventHandler, false);
   } else if (element.attachEvent) {
       element.attachEvent('on' + eventName, eventHandler);
   };
};
// Listen to message from child window
var results = document.getElementById('results');
var iframeEl = document.getElementsByName('iframe1');
var blink1 = 0;

bindEvent(blink1, window, 'message', function (e) {
    results.innerHTML = e.data;
    blink1 = setInterval(function () {
       results.style.opacity =
           (results.style.opacity == 0 ? 1 : 0);
    }, 1000);
});
iframeEl.onload =
   clearInterval(blink1);





//document.querySelector("button.SAVE").addEventListener("click", function () {
//  var html = document.querySelector("table").outerHTML;
//  var filename = "{{ walkname }}-data.csv";
//  export_table_to_csv(html, filename);
//  });
