// 🧱 Safe variable injection
  {% set _options = options or {} %}
  {% set _constants = constants or {} %}
  window.task_tags = {{ _options.get('task_tags', []) | tojson }};
  window.resources = {{ _options.get('resources', []) | tojson }};
  window.places = {{ _constants.get('places', []) | tojson }};
  window.areas = {{ _options.get('areas', []) | tojson }};

  console.log("Injected task_tags:", window.task_tags);
  console.log("Injected resources:", window.resources);
  console.log("Injected places:", window.places);
  console.log("Injected areas:", window.areas);

  window.DEVURLS = {{ DEVURLS | tojson }} ;
  window.isDev = location.hostname.includes("localhost") || location.hostname.startsWith("127.");
  window.API = window.isDev ? window.DEVURLS["dev"] : "__REPLACE_WITH_API_URL__";

  if (!window.isDev) {
      const btn = document.getElementById("export-html-btn");
      if (btn) {
          btn.style.display = "none";
      }
  }

  const startHour = 9, endHour = 21, slotDuration = 2;

  // ----------------------------
  // Flash Message Handling
  // ----------------------------
  const messages = {{ get_flashed_messages()|tojson|safe }} || [];

  const logList = document.querySelector("#logwin .flashes");
  function addMessageToLog(text) {
      if (!logList) return;

      const li = document.createElement("li");

      // Create timestamp
      const now = new Date();
      const hh = String(now.getHours()).padStart(2, "0");
      const mm = String(now.getMinutes()).padStart(2, "0");
      const ss = String(now.getSeconds()).padStart(2, "0");
      const timestamp = `[${hh}:${mm}:${ss}]`;

      li.textContent = `${timestamp} ${text}`;
      logList.appendChild(li);

      // Auto-scroll
      logList.scrollTop = logList.scrollHeight;
  }


  // Show flash messages from Flask (if any)
  messages.forEach(msg => addMessageToLog(msg));

  // ----------------------------
  // iframe postMessage handling
  // ----------------------------
  bindEvent(window, "message", (e) => {
      addMessageToLog(e.data?.type || String(e.data));
  });


  /* ---------------------------------------------------------
   * BUTTON → IFRAME ROUTING
   * --------------------------------------------------------- */
  const iframeButtons = {
      b3: "{{ url_for('stream_input') }}",
      b4: "{{ url_for('leafletting') }}",
      b5: "{{ url_for('kanban') }}",
      b6: "{{ url_for('telling') }}",
      b7: "{{ url_for('search') }}",
      b8: "{{ url_for('dashboard') }}"
  };
