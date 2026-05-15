
const f = function() {};
f.visibleColumnIds = [];
f.setVisibleColumnIds = () => {};
f.data = [];
f.loading = false;
f.error = null;
f.refetch = () => {};

const p = new Proxy(f, {
  get: (target, prop) => {
    if (prop in target) return target[prop];
    if (prop === 'prototype') return f.prototype;
    return p;
  },
  apply: () => p,
  construct: () => p
});
export { p as default, p as a, p as b, p as c, p as d, p as e, p as f, p as g, p as h, p as i, p as j, p as k, p as l, p as m, p as n, p as o, p as p, p as q, p as r, p as s, p as t, p as u, p as v, p as w, p as x, p as y, p as z, p as A, p as B, p as C, p as D, p as E, p as F, p as G, p as H, p as I, p as J, p as K, p as L, p as M, p as N, p as O, p as P, p as Q, p as R, p as S, p as T, p as U, p as V, p as W, p as X, p as Y, p as Z };