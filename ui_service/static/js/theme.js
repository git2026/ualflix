(() => {
  'use strict'
  const getStoredTheme = () => localStorage.getItem('theme')
  const setStoredTheme = theme => localStorage.setItem('theme', theme)

  // Obtém o tema preferido, com dark como padrão
  const getPreferredTheme = () => {
    const storedTheme = getStoredTheme()
    if (storedTheme) {
      return storedTheme
    }
    return 'dark'
  }
  const setTheme = theme => {
    document.documentElement.setAttribute('data-bs-theme', theme)
  }
  // Mostra o ícone de tema correspondente.
  setTheme(getPreferredTheme())
  const showActiveTheme = (theme, focus = false) => {
    const themeSwitcher = document.querySelector('#theme-toggler')
    if (!themeSwitcher) {
      return
    }
    const themeSwitcherIcon = themeSwitcher.querySelector('i')
    if (theme === 'light') {
        themeSwitcherIcon.classList.remove('bi-sun-fill');
        themeSwitcherIcon.classList.add('bi-moon-fill');
    } else {
        themeSwitcherIcon.classList.remove('bi-moon-fill');
        themeSwitcherIcon.classList.add('bi-sun-fill');
    }
    if (focus) {
      themeSwitcher.focus()
    }
  }

  // Configura o switcher de tema ao carregar a página.
  window.addEventListener('DOMContentLoaded', () => {
    showActiveTheme(getPreferredTheme())
    const themeToggler = document.getElementById('theme-toggler');
    if (themeToggler) {
        themeToggler.addEventListener('click', () => {
            const currentTheme = getPreferredTheme();
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setStoredTheme(newTheme);
            setTheme(newTheme);
            showActiveTheme(newTheme, true);
        });
    }
  })
})() 