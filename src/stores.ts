import type { Writable } from 'svelte/store';
import { writable } from 'svelte/store';

export function syncValue(model: any, name_: string) {
  const name: string = name_;
  const curVal: Writable<any> = writable(model.get(name));

  model.on('change:' + name, () => curVal.set(model.get(name)), null);

  return {
    set: (v: any) => {
      curVal.set(v);
      model.set(name, v);
      model.save_changes();
    },
    subscribe: curVal.subscribe,
    update: (func: any) => {
      curVal.update((v: any) => {
        let out = func(v);
        model.set(name, out);
        model.save_changes();
        return out;
      });
    },
  };
}
