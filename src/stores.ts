import type { Writable } from 'svelte/store';
import { writable } from 'svelte/store';

export function syncValue(model: any, name_: string, defaultVal: any) {
  const name: string = name_;
  const curVal: Writable<any> = writable(model.get(name) || defaultVal);

  model.on('change:' + name, (model: any, val: any) => curVal.set(val), null);

  if (!!model.onAttach)
    model.onAttach(async () => {
      let v = await model.fetch(name);
      curVal.set(v);
    });

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
