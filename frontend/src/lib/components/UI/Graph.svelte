<script lang="ts">
  import { onMount } from 'svelte';
  import { ScatterGL, Dataset } from 'scatter-gl';
  import type { ComplaintData } from '$lib/type/index';

  let containerElement: HTMLDivElement;
  let tooltip: HTMLElement;

  // Replace with your actual data
  export let points: ComplaintData[];
 
let selectedClusterCount: string = 'All';
let selectedCategory: string = 'All';

// Compute unique categories for the category dropdown.
const categories = Array.from(new Set(points.map(p => p.CATEGORY)));

 
const clusterCountMap = new Map<string, number>();
points.forEach(p => {
  const cl = p.cluster.toString();
  clusterCountMap.set(cl, (clusterCountMap.get(cl) || 0) + 1);
});
 
const sortedClustersGlobal = Array.from(clusterCountMap.entries())
  .sort((a, b) => b[1] - a[1])
  .map(entry => entry[0]);
 
let clusterOptions: string[] = ['All'];
for (let i = 1; i <= sortedClustersGlobal.length; i++) {
  clusterOptions.push(i.toString());
}



const clusterSeed = 12345;   
const categorySeed = 67890;  
const contrastThreshold = 30; 

const clusterColors = new Map<string, string>();
const categoryColors = new Map<string, string>();
 
const seededHash = (str: string, seed: number): number => {
let hash = seed;
for (let i = 0; i < str.length; i++) {
  hash = (hash * 31 + str.charCodeAt(i)) >>> 0;  
}
return hash;
};

// Helper to check if two hues are too similar.
const isHueSimilar = (hue1: number, hue2: number) => {
const diff = Math.abs(hue1 - hue2);
return diff < contrastThreshold || (360 - diff) < contrastThreshold;
};

// Helper to extract the hue value from an HSL string like "hsl(123, 70%, 50%)".
const extractHue = (hsl: string): number => {
const hueStr = hsl.slice(4, hsl.indexOf(','));
return parseInt(hueStr, 10);
};

 
const getDistinctColor = (key: string, colorMap: Map<string, string>, seed: number): string => {
if (colorMap.has(key)) return colorMap.get(key)!;

 
let baseHash = seededHash(key, seed);
let hue = baseHash % 360;
 
let attempts = 0;
while (true) {
  let distinct = true;
  for (const [, color] of colorMap.entries()) {
    const existingHue = extractHue(color);
    if (isHueSimilar(hue, existingHue)) {
      distinct = false;
      break;
    }
  }
  if (distinct) break;
  hue = (hue + contrastThreshold) % 360;
  attempts++;
  if (attempts > 12) break; // Prevent an infinite loop if too many colors exist.
}
const color = `hsl(${hue}, 70%, 50%)`;
colorMap.set(key, color);
return color;
};

const getColorForCluster = (cluster: string): string => {
return getDistinctColor(cluster, clusterColors, clusterSeed);
};

const getColorForCategory = (category: string): string => {
return getDistinctColor(category, categoryColors, categorySeed);
};


let scatterGL: ScatterGL;
let dataset: Dataset;
let precomputedColors: string[] = [];

 
const computeColors = () => {
 
  let topClusters = new Set<string>();
  const clusterActive = selectedClusterCount !== 'All';
  if (clusterActive) {
    const count = parseInt(selectedClusterCount);
    // Use the globally computed sortedClustersGlobal to get the top N clusters.
    sortedClustersGlobal.slice(0, count).forEach(cl => topClusters.add(cl));
  }
  const categoryActive = selectedCategory !== 'All';

  precomputedColors = points.map(p => {
    const pClusterStr = p.cluster.toString();
    const matchCluster = topClusters.has(pClusterStr);
    const matchCategory = p.CATEGORY === selectedCategory;

    if (clusterActive || categoryActive) {
      if ((clusterActive && matchCluster) || (categoryActive && matchCategory)) {
 
        if (clusterActive && matchCluster) {
          return getColorForCluster(pClusterStr) || '#000000';
        } else {
          return getColorForCategory(p.CATEGORY) || '#000000';
        }
      } else {
        return '#d3d3d3';
      }
    }
 
    return getColorForCategory(p.CATEGORY) || '#000000';
  });
};

 
const pointColorer = (index: number) => precomputedColors[index];

const initializeScatterGL = () => {
  dataset = new Dataset(points.map(p => [p.x, p.y]));
  computeColors();
  scatterGL = new ScatterGL(containerElement, {
    pointColorer,
    onHover: (pointIndex: number) => {
      if (pointIndex != null) {
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
    orbitControls: {
      zoomSpeed: 1.75,
    },
  });
  scatterGL.render(dataset);
};

onMount(() => {
  initializeScatterGL();
});

 
$: {
  // Dummy dependency to ensure reactivity.
  const dummy = selectedClusterCount + selectedCategory;
  if (scatterGL) {
    computeColors();
 
    dataset = new Dataset(points.map(p => [p.x, p.y]));
    scatterGL.render(dataset);
  }
}
</script>

<div>
<label for="clusterSelect">Select Number of Clusters to Highlight:</label>
<select id="clusterSelect" bind:value={selectedClusterCount} on:change={() => { selectedCategory = 'All'; }}>
  {#each clusterOptions as option}
    <option value={option}>{option}</option>
  {/each}
</select>

<label for="categorySelect">Select Category:</label>
<select id="categorySelect" bind:value={selectedCategory} on:change={() => { selectedClusterCount = 'All'; }}>
  <option value="All">All</option>
  {#each categories as category}
    <option value={category}>{category}</option>
  {/each}
</select>
</div>

<div bind:this={containerElement} class="w-[1800px] h-[800px] relative"></div>
<div bind:this={tooltip} class="absolute hidden bg-black/70 text-white p-2 rounded pointer-events-none"></div>
