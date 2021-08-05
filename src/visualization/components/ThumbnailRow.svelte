<script>
  export let d;
  export let color;
  export let blobURLs;

  function makeText(item) {
    if (!item || (!item.text && !item.description)) return '';
    // let textColor = color;
    // let color = 'black';
    // if (secondary && diff.size > 0 && !diff.has(item.id)) {
    //   color = diffColor;
    // }
    let infoText = `<p style="color: ${color}">` + (item.text || '') + '</p>';
    // if (!secondary && !!item.description) {
    //   infoText +=
    //     '<p style="color: grey;">' +
    //     item.description.replace('\n', '</p><p style="color: grey;">') +
    //     '</p>';
    // }
    return infoText;
  }
</script>

<div class="thumbnail-row">
  {#if !!d.sheet}
    <div
      class="image-parent"
      style={`width: ${d.spec.frame.w}px; height: ${d.spec.frame.h}px;`}
    >
      <img
        class="thumbnail-image"
        src={blobURLs.get(d.sheet)}
        width={`${d.macroSize.w}px`}
        height={`${d.macroSize.h}px`}
        style={`left: ${-d.spec.frame.x}px; top: ${-d.spec.frame.y}px; width: ${
          d.macroSize.w
        }px; height: ${d.macroSize.h}px;`}
        alt="Image preview for point {d.id}"
      />
    </div>
  {/if}
  <div class="thumbnail-text-section">
    {@html makeText(d)}
  </div>
</div>


<style>
  .diff-red {
    border: 2px solid red;
  }

  .diff-green {
    border: 2px solid green;
  }
</style>