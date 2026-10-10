// MYRA Browser Bridge intentionally does not read cookies, passwords, or local storage.
// Page interaction is initiated by the extension service worker only after a user-authorized action.
(() => {
  if (window.__MYRA_BROWSER_BRIDGE__) return;
  Object.defineProperty(window, "__MYRA_BROWSER_BRIDGE__", {
    value: true,
    configurable: false,
    enumerable: false,
    writable: false
  });
})();
