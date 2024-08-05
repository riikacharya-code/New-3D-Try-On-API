import streamlit as st
import requests

import base64
import os
import sys

import replicate
from functools import wraps

# Set the API endpoints
IMGBB_API_ENDPOINT = "https://api.imgbb.com/1/upload"
IMGBB_API_KEY = "bccd65ab8da85ebc87c6a9d81e41d1de"


def run_vton(input, garm_list, category_list):

    if (not garm_list) or (not category_list):
        return input['human_img'] 

    input['garm_img'] = garm_list[0]
    input['category'] = category_list[0]

    garm_list.remove(garm_list[0])
    category_list.remove(category_list[0])

    vton_output = replicate.run( 
        "cuuupid/idm-vton:906425dbca90663ff5427624839572cc56ea7d380343d13e2a4c4b09d3f0c30f", 
        input=input
    )
    input['human_img'] = vton_output

    return run_vton(input, garm_list, category_list)




def generate_3d_from_vton(data): 
    

        api_token = data['api_token']
        if not api_token:
            st.error(f"Error: Must input API token")

        print("Received new request for /generate_3d_from_vton", file=sys.stderr)

        os.environ["REPLICATE_API_TOKEN"] = api_token
        
        # Validate that required fields are present
        if 'human_img' not in data or 'upper_body_img' not in data or 'lower_body_img' not in data:
            st.error(f"Error: Human Image, Upper Body Image, or Lower Body Image")
            
        # First model: cuuupid/idm-vton
        vton_input = {
            "human_img": data['human_img'],
            "crop": True,
            "seed": data.get('seed', 30),
            "steps": 40,
            "mask_only": False,
            "force_dc": False,
            "garment_des": ''
        }

        garm_list = [data.get('lower_body_img'), data.get('upper_body_img')]
        category_list = ['lower_body', 'upper_body']

        vton_output = run_vton(vton_input, garm_list, category_list)

        generated_image_url = vton_output[0] if isinstance(vton_output, list) else vton_output
        
        print("Generated image URL:", generated_image_url)

        dmg_input = {
            "seed": data.get('seed', 42),
            "image_path": generated_image_url,
            "export_video": True,
            "sample_steps": 300,
            "export_texmap": False,
            "remove_background": True
        }

        print("Running 3DMG model...")
        dmg_output = replicate.run(
            "deepeshsharma2003/3dmg:476f025230580cb41ffc3b3d6457965f968c63d1db4a0737bef338a851eb62d6",
            input=dmg_input
        )

        return dmg_output[1]
    



def upload_to_imgbb(image_file):
    img_bytes = image_file.getvalue()
    base64_image = base64.b64encode(img_bytes).decode('utf-8')
    
    payload = {
        "key": IMGBB_API_KEY,
        "image": base64_image,
    }
    
    response = requests.post(IMGBB_API_ENDPOINT, payload)
    if response.status_code == 200:
        return response.json()['data']['url']
    else:
        st.error(f"Failed to upload image to ImgBB. Status code: {response.status_code}")
        return None




st.title("Virtual Try-On and 3D Model Generator")

# Input for API token
api_token = st.text_input("Enter your Replicate API token. Sign up for ReplicateAI and obtain a token if you do not have one already:", type="password")

# File upload for human image
human_img_file = st.file_uploader("Upload human image", type=["png", "jpg", "jpeg"])

# File upload for upper body garment
upper_body_img_file = st.file_uploader("Upload upper body garment image", type=["png", "jpg", "jpeg"])

# File upload for lower body garment
lower_body_img_file = st.file_uploader("Upload lower body garment image", type=["png", "jpg", "jpeg"])

# Input for seed
seed = st.number_input("Enter seed value (optional):", value=30, step=1)

if st.button("Generate 3D Model"):
    if not api_token:
        st.error("Please enter your VTON API token.")
    elif not human_img_file or not upper_body_img_file or not lower_body_img_file:
        st.error("Please upload all required images.")
    else:
        # Upload images to ImgBB
        with st.spinner("Uploading images..."):
            human_img_url = upload_to_imgbb(human_img_file)
            upper_body_img_url = upload_to_imgbb(upper_body_img_file)
            lower_body_img_url = upload_to_imgbb(lower_body_img_file)

        if human_img_url and upper_body_img_url and lower_body_img_url:
            # Prepare the data for the VTON API
            data = {
                "api_token": api_token,
                "human_img": human_img_url,
                "upper_body_img": upper_body_img_url,
                "lower_body_img": lower_body_img_url,
                "seed": seed,
            }

            # Make the API request to the VTON service
            with st.spinner("Generating 3D model..."):
                try:
                    result = generate_3d_from_vton(data)
                    print(result)
                except requests.exceptions.RequestException as e:
                    st.error(f"Error communicating with the VTON API: {str(e)}")
                else:
                    
                    if result:
                        st.success("3D model generated successfully!")
                        st.video(result)
                    else:
                            st.error("The API response did not contain a result.")
        else:
            st.error("Failed to upload one or more images to ImgBB.")

# Preview uploaded images
if human_img_file:
    st.image(human_img_file, caption="Uploaded Human Image", use_column_width=True)
if upper_body_img_file:
    st.image(upper_body_img_file, caption="Uploaded Upper Body Garment", use_column_width=True)
if lower_body_img_file:
    st.image(lower_body_img_file, caption="Uploaded Lower Body Garment", use_column_width=True)

st.markdown("---")
st.markdown("Made with ❤️ by Riik Acharya")
