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
  export let thumbnail = false;

  // Point display attributes
  export let pointRadius = 3.0; // this component reads this information
  export let rFactor = 1.0; // this component writes the rFactor
  export let showPointBorders = true; // this component decides whether to show point borders

  // If this is non-empty, rFactor will be based on the point distances in the
  // visibleIDs list. Otherwise, it will use a random sample of points in the
  // dataset.
  export let visibleIDs = [];

  // Data is used to determine how much the viewport should be allowed to scale by
  export let data = null;

  let scales = new Scales([0, 1], [0, 1], [0, 1], [0, 1], padding);
  export let scalesNeutral = true;

  export let followingMarks = [];

  // Rescaling

  $: if (!!width && !!height && !!xExtent && !!yExtent) {
    scales = new Scales(xExtent, yExtent, [0, width], [0, height], padding);
  }

  $: if (!!scales && !!data && !thumbnail) {
    updateScaleBounds(true);
  }

  let oldVisibleIDs = [];
  $: if (oldVisibleIDs !== visibleIDs) {
    if (!!scales && !!data) {
      updateScaleBounds();
      // updatePointDisplay();
    }
    oldVisibleIDs = visibleIDs;
  }

  let minPointDistance = null;
  let _defaultMinPointDistance = null;
  const MinPointPixelDistance = 50;

  function updateScaleBounds(reset = false) {
    // Look at the distance between each point and its nearest neighbor, and
    // set the max scale such that the closest distance can scale to a certain
    // number of pixels

    if (visibleIDs.length > 0) {
      minPointDistance =
        computeMinPointDistance(visibleIDs) || _defaultMinPointDistance;
    } else {
      if (_defaultMinPointDistance == null || reset) {
        _defaultMinPointDistance = computeMinPointDistance() || 1.0;
        scales.maxScale = scales.scaleFactorForDistance(
          minPointDistance,
          MinPointPixelDistance
        );
      }
      minPointDistance = _defaultMinPointDistance;
    }
  }

  function computeMinPointDistance(ids = null) {
    let collectedDistances = [];
    let neighborMembershipSet = ids != null ? new Set(ids) : null;
    data.frames.forEach((frame) => {
      let idsToTest = ids != null ? ids : frame.getIDs();
      idsToTest.forEach((id) => {
        if (Math.random() < 100 / idsToTest.length) {
          let point = frame.byID(id);
          let neighbors = frame.neighbors(id, 25);
          if (neighborMembershipSet != null) {
            neighbors = neighbors.filter((n) => neighborMembershipSet.has(n));
          }
          if (neighbors.length == 0) return;
          let idx = Math.floor(Math.random() * neighbors.length);
          collectedDistances.push(
            euclideanDistance(point, frame.byID(neighbors[idx]))
          );
        }
      });
    });

    if (collectedDistances.length > 0) {
      collectedDistances.sort((a, b) => a - b);
      return collectedDistances[Math.round(collectedDistances.length * 0.1)];
    }
    return null;
  }

  $: if (!!scales) {
    scales.onUpdate(() => {
      scalesNeutral = scales.isNeutral();
      updatePointDisplay();
      dispatch('update');
    });
  }

  function updatePointDisplay() {
    // Add an rFactor property indicating how much to scale the points by for
    // appropriate display
    if (minPointDistance != null) {
      // Compute the radius required so that two points at 2 * minPointDistance
      // don't overlap based on pointRadius
      let scale =
        scales.getDataToUniformScaleFactor() * scales.scaleFactor.get();
      rFactor = Math.max(
        Math.min((minPointDistance * 1.5 * scale) / (2 * pointRadius), 1.0),
        0.2
      );

      showPointBorders = minPointDistance * scale >= 10;
    } else {
      let scale = scales.scaleFactor.get();
      rFactor = Math.min(scale / 5.0, 1.0);
      showPointBorders = scale >= 1.0;
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
