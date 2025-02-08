<script lang="ts">
  import { onMount } from 'svelte';
  import { ScatterGL, Dataset } from 'scatter-gl';
  import type { ComplaintData } from "$lib/type/index";

  let containerElement: HTMLDivElement;
  let tooltip: HTMLElement;

  export let points: ComplaintData[];
  const categoryColors = new Map<string, string>();
  const getColorForCategory = (category: string) => {
    if (!categoryColors.has(category)) {
      const color = `hsl(${Math.random() * 360}, 70%, 50%)`; // Random color
      categoryColors.set(category, color);
    }
    return categoryColors.get(category);
  };
  onMount(() => {
    const dataset = new Dataset(points.map(p => [p.x, p.y, p.z]));  
    const scatterGL = new ScatterGL(containerElement, {
      pointColorer: (index) => {
        return getColorForCategory(points[index].CATEGORY) || "#000000"; // Default to black if undefined
      },
      onHover: (pointIndex) => {
        if (pointIndex !== null) {
          const data = points[pointIndex];
  
          tooltip.style.left = `${event.clientX + 10}px`;
          tooltip.style.top = `${event.clientY + 10}px`;
          tooltip.innerHTML = `
            <strong>Complaint ID:</strong> ${data.COMPLAINT_ID} <br>
            <strong>Category:</strong> ${data.CATEGORY} <br>
            <strong>Summary:</strong> ${data.COMPLAINT_SUMMARY}
          `;
          tooltip.style.display = 'block';
        } else {
          tooltip.style.display = 'none';  
        }
      },
      onClick: (pointIndex: number | null) => {
        console.log(`Clicked on point ${pointIndex}`);
      },
      orbitControls: {
        zoomSpeed: 1.75,
      },


    });
    scatterGL.render(dataset);
  });
</script>
 
<div bind:this={containerElement} style="width: 1800px; height: 800px; position: relative;"></div>
 
<div bind:this={tooltip} style="position: absolute; display: none; background: rgba(0, 0, 0, 0.7); color: white; padding: 8px; border-radius: 4px; pointer-events: none;"></div>
