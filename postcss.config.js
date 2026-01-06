module.exports = {
  plugins: {
    '@tailwindcss/postcss': {},
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