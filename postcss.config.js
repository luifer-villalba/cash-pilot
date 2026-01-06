module.exports = {
  plugins: {
    '@tailwindcss/postcss': {},
    'postcss-preset-env': {
      stage: 2, // Enable features that are stable
      features: {
        // Note: oklch() conversion is handled by CSS fallbacks in input.css
        // postcss-preset-env doesn't have native oklch() support yet
        'color-mix': false, // Don't use color-mix (we removed it)
        'logical-properties-and-values': false, // Don't convert logical properties
        'is-pseudo-class': false, // Disable to avoid warnings about complex selectors
        'cascade-layers': false, // Disable to avoid revert-layer warnings
      },
      browsers: [
        '> 0.5%',
        'last 2 versions',
        'Firefox ESR',
        'not dead',
        'IE 11', // Windows 7 support
        'Chrome >= 50', // Windows 7 support
        'Firefox >= 45', // Windows 7 support
      ],
    },
    autoprefixer: {
      // Support older browsers including Windows 7 (Chrome 109, Firefox 115, IE11)
      overrideBrowserslist: [
        '> 0.5%',
        'last 2 versions',
        'Firefox ESR',
        'not dead',
        'IE 11', // Windows 7 support
        'Chrome >= 50', // Windows 7 support
        'Firefox >= 45', // Windows 7 support
      ],
    },
  },
}