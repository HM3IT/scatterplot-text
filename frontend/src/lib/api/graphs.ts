import { env } from '$env/dynamic/public';


export const uploadFile = async (file: File) => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${env.PUBLIC_API_URL}/api/graphs/generate`, {
      method: 'POST',
      body: formData, 
      headers: {
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    console.log('Response:', data);
    return data;
  } catch (error) {
    console.error('File upload failed:', error);
    throw error;
  }
};
