import './app.css';
import App from './App.svelte';

function render(view) {
  const app = new App({
    target: view.el,
    props: {
      model: view.model,
    },
  });
}

export default { render };
