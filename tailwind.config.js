// tailwind.config.js
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js"
  ],
  safelist: [
    // Light theme gradient backgrounds
    { pattern: /from-(blue|purple|amber|red|emerald|sky|green|info)-50/ },
    { pattern: /from-(blue|purple|amber|red|emerald|sky|green|info)-(500|500\/10|500\/20)/ },
    { pattern: /border-(blue|purple|amber|red|emerald|sky|green|info)-(200|800)/ },
    { pattern: /text-(blue|purple|amber|red|emerald|sky|green|info)-(700|400|600|500)/ },
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require("daisyui")
  ],
  daisyui: {
    themes: ["light", "dark"],
  },
}