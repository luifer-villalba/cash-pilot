// tailwind.config.js
// Note: Tailwind v4 uses CSS-based configuration (@import, @plugin in input.css)
// This file is kept for content paths and safelist patterns
// Plugins (DaisyUI, Forms) are configured in static/css/input.css
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js"
  ],
  safelist: [
    // Light theme gradient backgrounds
    // These patterns ensure dynamic classes are included even if not detected
    { pattern: /from-(blue|purple|amber|red|emerald|sky|green|info)-50/ },
    { pattern: /from-(blue|purple|amber|red|emerald|sky|green|info)-(500|500\/10|500\/20)/ },
    { pattern: /border-(blue|purple|amber|red|emerald|sky|green|info)-(200|800)/ },
    { pattern: /text-(blue|purple|amber|red|emerald|sky|green|info)-(700|400|600|500)/ },
  ],
  // Note: theme, plugins, and daisyui config moved to CSS (input.css)
}