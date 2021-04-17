<script>
  export let width = 200;
  export let height = 600;

  export let thumbnailData = null;
  export let primaryTitle = "Selected item";
  export let secondaryTitle = "Neighbors";
  export let primaryThumbnail = null;
  export let secondaryThumbnails = [];
  export let secondaryDiff = []; // list of IDs to use as references
  export let diffColor = "green";
  export let frame = -1;
  export let message = "";

  let primaryText = "";
  let secondaryTexts = [];

  let _secondaryDiff = new Set();
  $: _secondaryDiff = new Set(secondaryDiff);

  function makeThumbnailInfo(id, secondary, diff) {
    if (!thumbnailData || !id) return "";
    let item = thumbnailData.items["" + id];
    if (!item) return "";

    let color = "black";
    if (secondary && diff.size > 0 && !diff.has(id)) {
      color = diffColor;
    }
    let infoText = `<p style="color: ${color}">` + (item.name || "") + "</p>";
    if (!secondary && !!item.description) {
      infoText +=
        '<p style="color: grey;">' +
        item.description.replace("\n", '</p><p style="color: grey;">') +
        "</p>";
    }
    if (!secondary && frame >= 0 && !!item.frames && !!item.frames[frame]) {
      infoText += "<p><strong>In frame " + frame + ":</strong></p>";
      infoText +=
        '<p style="color: grey;">' +
        item.frames[frame].replace("\n", '</p><p style="color: grey;">') +
        "</p>";
    }
    return infoText;
  }

  $: secondaryTexts = secondaryThumbnails.map((t) =>
    makeThumbnailInfo(t, true, _secondaryDiff)
  );

  $: primaryText = makeThumbnailInfo(primaryThumbnail, false);
</script>

<div style="width: {width}px; height: {height}px;">
  <h4>{primaryTitle}</h4>
  {#if !!message}
    <p>{message}</p>
  {/if}
  {@html primaryText}
  <h4>{secondaryTitle}</h4>
  {#each secondaryTexts as text}
    {@html text}
  {/each}
</div>

<style>
</style>
