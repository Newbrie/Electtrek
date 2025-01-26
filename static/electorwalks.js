
// addEventListener support for IE8
// Listen to message from child window
var results = document.getElementById('results');
var iframeEl = document.getElementsByName('iframe1');

function bindEvent( element, eventName, eventHandler) {
   if (element.addEventListener){
       element.addEventListener(eventName, eventHandler, false);
   } else if (element.attachEvent) {
       element.attachEvent('on' + eventName, eventHandler);
   };
};

bindEvent( window, 'message', function (e) {
    results.innerHTML = e.data;
    const blink1 = setInterval(function () {
       results.style.opacity =
           (results.style.opacity == 0 ? 1 : 0);
    }, 1000);
    results.id = blink1;
    alert("_____blink:"+results.id);
});

iframeEl.onload = clearInterval(results.id);


//document.querySelector("button.SAVE").addEventListener("click", function () {
//  var html = document.querySelector("table").outerHTML;
//  var filename = "{{ walkname }}-data.csv";
//  export_table_to_csv(html, filename);
//  });
