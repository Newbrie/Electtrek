
// addEventListener support for IE8
// Listen to message from child window

          const pessages = [];
          var pack = JSON.parse('{{ get_flashed_messages()|tojson|safe }}');

          for (let x in pack) {
            pessages.push(pack[x]);
          };

          var iframeEl = document.getElementsByName('iframe1');

          function bindEvent( element, eventName, eventHandler) {
             if (element.addEventListener){
                 element.addEventListener(eventName, eventHandler, false);
             } else if (element.attachEvent) {
                 element.attachEvent('on' + eventName, eventHandler);
             };
          };

          bindEvent( window, 'message', function (e) {
              pessages.push(e.data);
              alert("_____blink:"+pessages);
          });

          function get_childframe_messages() {
            return JSON.stringify(pessages);
          };




//document.querySelector("button.SAVE").addEventListener("click", function () {
//  var html = document.querySelector("table").outerHTML;
//  var filename = "{{ walkname }}-data.csv";
//  export_table_to_csv(html, filename);
//  });
