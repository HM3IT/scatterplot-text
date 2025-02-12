<script lang="ts">
 
    import type {Point2D, PointMetadata} from 'scatter-gl';
    import type { ComplaintData } from '$lib/type/index';
  
    import { onMount } from 'svelte';
    import {distinctColors} from "$lib/utils/constant";
  
    import { ScatterGL, Dataset } from 'scatter-gl';
   
   
    let points:ComplaintData[] = [
          {
              "COMPLAINT_ID": "C200",
              "CONTRACT_ID": "CT1200",
              "PARENT_ORGANIZATION": "GreenTech Solutions",
              "REGION_RESPONSIBLE": "South America",
              "CATEGORY": "Service",
              "SUBCATEGORY": "Service Interruption",
              "SUBCATEGORY_OTHER": "",
              "COMPLAINT_SUMMARY": "Service was unavailable for 48 hours without prior notice.",
              "UPDATED_DATE": "2027-08-09",
              "CASEWORK": "Closed",
              "COMMENT_TEXT": "Provided a service credit and improved communication protocols.",
              "COMPLAINANT_TYPE": "Business",
              "STATE": "BR",
              "x": -4.7666406631,
              "y": -1.4300470352,
              "z": -8.8019895554,
              "cluster": 26,
              "topic": "Chatbot failure and service disruption in customer support system."
          }
        ]
   
  
    fetch("src/lib/data/umap_data.json")
    .then((res) => res.json())
    .then((data) => {
      points = [...points, ...data]
      
    })
    .catch((e) => console.error(e));
  
    let containerElement: HTMLDivElement;
    let tooltip: HTMLElement;
    let scatterGL: ScatterGL;
   
    // const renderMode = "POINT"
    const clusterColors = new Map();
    const categoryColors = new Map();
    const clusterCountMap = new Map<string, number>();
    const categories = Array.from(new Set(points.map(p => p.CATEGORY)));
    
    let precomputedColors: string[] = [];
    let point2D:Point2D[] = []
    let pointMetadata:PointMetadata[] = []
  
    let selectedClusterCount: string = 'All';
    let selectedCategory: string = 'All';
    let clusterOptions: string[] = ['All'];
    
  
    points.forEach(point=>{
      point2D.push([point.x, point.y])
      pointMetadata.push({
        label: point.COMPLAINT_ID,
        summary: point.COMPLAINT_SUMMARY,
        comment: point.COMMENT_TEXT
      })
  
      const cl = point.cluster.toString();
      clusterCountMap.set(cl, (clusterCountMap.get(cl) || 0) + 1);
    })
   
    const dataset:Dataset =  new Dataset(point2D, pointMetadata);
    const sortedClustersGlobal = Array.from(clusterCountMap.entries())
      .sort((a, b) => b[1] - a[1])
      .map(entry => entry[0]);
  
    
    for (let i = 1; i <= sortedClustersGlobal.length; i++) {
      clusterOptions.push(i.toString());
    }
  
    const getColorForCluster = (cluster:string) => {
      if (!clusterColors.has(cluster)) {
        const index = clusterColors.size % distinctColors.length;
        clusterColors.set(cluster, distinctColors[index]);
      }
      return clusterColors.get(cluster);
    };
  
    const getColorForCategory = (category:string) => {
      if (!categoryColors.has(category)) {
        const index = categoryColors.size % distinctColors.length;
        categoryColors.set(category, distinctColors[index]);
      }
      return categoryColors.get(category);
    };
  
  
    const updateColors = () => {
   
      let topClusters = new Set<string>();
      const clusterActive = selectedClusterCount !== 'All';
      if (clusterActive) {
        const count = parseInt(selectedClusterCount);
   
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
  
    const initializeScatterGL = () => {
     
      updateColors();
      scatterGL = new ScatterGL(containerElement, {
        pointColorer:(index: number) => precomputedColors[index],
        // renderMode,
        showLabelsOnHover: false,
        onHover: (pointIndex:number| null) => {
          if (pointIndex !== null && pointIndex >= 0 && pointIndex < points.length) {
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
        styles: {
          axesVisible: true
        },
        orbitControls: {
          zoomSpeed: 1.75,
        },
   
       
    
      });
      scatterGL.render(dataset);
    };
  
    onMount(async() => {
      initializeScatterGL();
    });
  
    
  $: {
    // Dummy dependency to ensure reactivity.
    const dummy = selectedClusterCount + selectedCategory;
    if (scatterGL) {
      updateColors();
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
  
  <div bind:this={containerElement} class="w-full h-full relative">
    
  </div>
  <div bind:this={tooltip} class="absolute bg-black bg-opacity-70 text-white p-1.5 rounded pointer-events-none hidden z-50"> </div>
  