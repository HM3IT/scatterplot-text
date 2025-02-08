<script lang="ts">
	import Graph from '$lib/components/UI/Graph.svelte';
  import DropFile from '@svelte-parts/drop-file';
  import { uploadFile } from '$lib/api/graphs';
  import type { ComplaintData } from "$lib/type/index";
 
  let fileOver = false;
  let isUploaded = false;
  let result: ComplaintData[];

  const onDrop = async (files: File[]) => {
 
  alert(`Files: ${files.map(d => d.name).join(', ')}`)
  fileOver = false;
    try {
      for (const file of files) {
        result = await uploadFile(file);
        isUploaded = true;
        console.log('File uploaded successfully:', result);
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      isUploaded = false;
    }
  };

  const onEnter = () => {
    fileOver = true;
  };

  const onLeave = () => {
    fileOver = false;
  };
</script>

<style>
  body{
      margin: 0;
      padding: 0;
      width: 100%;
      height: 100dvh;
  }
  .drop-zone {
      border: 2px dashed #ccc;
      padding: 20px;
      text-align: center;
      transition: background-color 0.3s;
      display: grid;
      align-items: center;
      margin: auto;
      width: 800px;
      height: 300px;
      /* background-color: gray; */
      color: black;
      margin: auto;
  }

  .over {
      background-color: white;
      color: blue;
   
  }

  .drop-zone.over {
      background-color: #f0f0f0;
      border: black solid 2px;
  }

</style>

{#if !isUploaded}
<DropFile class="h-12" onDrop={onDrop} onEnter={onEnter} onLeave={onLeave}>
  <div class={`drop-zone ${fileOver ? 'over' : ''}`}>
    {fileOver ? 'Release to upload files' : 'Drag and drop files here or click to select files'}
  </div>
</DropFile>

{:else}
<Graph points={result}></Graph>

{/if}
