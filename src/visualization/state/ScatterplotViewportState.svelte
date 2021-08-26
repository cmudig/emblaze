<!-- Script-only component that manages the view-specific state (e.g. scales) -->
<svelte:options accessors />

<script>
  import { createEventDispatcher } from 'svelte';
  import { Scales } from '../models/scales';
  import { euclideanDistance } from '../utils/helpers';

  const dispatch = createEventDispatcher();

  // State props
  export let width = null;
  export let height = null;
  export let padding = 0.3;
  export let xExtent = null;
  export let yExtent = null;

  export let pointRadius = 3.0;
  export let rFactor = 1.0;

  // Data is used to determine how much the viewport should be allowed to scale by
  export let data = null;

  let scales = new Scales([0, 1], [0, 1], [0, 1], [0, 1], padding);
  export let scalesNeutral = true;

  export let followingMarks = [];

  // Rescaling

  $: if (!!width && !!height && !!xExtent && !!yExtent) {
    scales = new Scales(xExtent, yExtent, [0, width], [0, height], padding);
  }

  $: if (!!scales && !!data) {
    updateScaleBounds();
  }

  let minPointDistance = null;

  function updateScaleBounds() {
    // Look at the distance between each point and its nearest neighbor, and
    // set the max scale such that the closest distance can scale to a certain
    // number of pixels

    let pixelDistance = 50;
    let collectedDistances = [];
    data.frames.forEach((frame) => {
      let ids = frame.getIDs();
      ids.forEach((id) => {
        if (Math.random() < 100 / ids.length) {
          let point = frame.byID(id);
          if (!point.highlightIndexes) return;
          let dist = euclideanDistance(
            point,
            frame.byID(point.highlightIndexes[0])
          );
          collectedDistances.push(dist);
        }
      });
    });

    collectedDistances.sort((a, b) => a - b);
    minPointDistance =
      collectedDistances[Math.min(10, collectedDistances.length)];
    scales.maxScale = scales.scaleFactorForDistance(
      minPointDistance,
      pixelDistance
    );
  }

  $: if (!!scales) {
    scales.onUpdate(() => {
      scalesNeutral = scales.isNeutral();
      updateRFactor();
      dispatch('update');
    });
  }

  function updateRFactor() {
    // Add an rFactor property indicating how much to scale the points by for
    // appropriate display
    if (minPointDistance != null) {
      // Compute the radius required so that two points at 2 * minPointDistance
      // don't overlap based on pointRadius
      let scale =
        scales.getDataToUniformScaleFactor() * scales.scaleFactor.get();
      rFactor = Math.max(
        Math.min((minPointDistance * scale) / (2 * pointRadius), 1.0),
        0.2
      );
    } else {
      rFactor = Math.min(scales.scaleFactor.get() / 5.0, 1.0);
    }
  }

  // Following

  $: if (!!scales) {
    if (followingMarks.length > 0) {
      scales.follow(followingMarks);
      dispatch('update');
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
    dispatch('update');
  }

  export function translateBy(dx, dy) {
    scales.translateBy(dx, dy);
    dispatch('update');
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
