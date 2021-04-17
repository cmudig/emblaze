<!-- Script-only component that manages the view-specific state (e.g. scales) -->
<svelte:options accessors />

<script>
  import { createEventDispatcher } from "svelte";
  import { Scales } from "../models/scales";

  const dispatch = createEventDispatcher();

  // State props
  export let width = null;
  export let height = null;
  export let padding = 0.3;
  export let xExtent = null;
  export let yExtent = null;

  let scales = new Scales([0, 1], [0, 1], [0, 1], [0, 1], padding);
  export let scalesNeutral = true;

  export let followingMarks = [];

  // Rescaling

  $: if (!!width && !!height && !!xExtent && !!yExtent) {
    scales = new Scales(xExtent, yExtent, [0, width], [0, height], padding);
  }

  $: if (!!scales) {
    scales.onUpdate(() => {
      scalesNeutral = scales.isNeutral();
      dispatch("update");
    });
  }

  // Following

  $: if (!!scales) {
    if (followingMarks.length > 0) {
      scales.follow(followingMarks);
      dispatch("update");
    } else {
      scales.unfollow();
    }
  }

  // Methods

  export function advance(dt) {
    if (!scales) return false;
    return scales.advance(dt);
  }

  export function resetAxisScales() {
    scales.resetZoom();
  }

  export function scaleBy(ds, centerPoint) {
    scales.scaleBy(ds, centerPoint);
    dispatch("update");
  }

  export function translateBy(dx, dy) {
    scales.translateBy(dx, dy);
    dispatch("update");
  }

  export function scaleX(val) {
    return scales.scaleX(val);
  }
  export function scaleY(val) {
    return scales.scaleY(val);
  }

  // Returns values that can be used to transform raw x, y coordinates into
  // screen-space.
  export function getTransformInfo() {
    return scales.getTransformInfo();
  }
</script>
