
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model
from sklearn.model_selection import train_test_split
from tensorflow.keras.optimizers import Adam

# Constants
XRAY_DATASET_ROOT = os.path.join(os.path.dirname(__file__), 'xray_dataset')
DATA_CSV = os.path.join(XRAY_DATASET_ROOT, 'Data_Entry_2017.csv')
MODEL_PATH = 'disease_model.keras'
IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32

# Load the data
df = pd.read_csv(DATA_CSV)

print(df.head())

# Get all unique labels
all_labels = np.unique([item for sublist in df['Finding Labels'].str.split('|') for item in sublist])

# One-hot encode the labels
for label in all_labels:
    if label != 'No Finding':
        df[label] = df['Finding Labels'].apply(lambda x: 1 if label in x else 0)

# Create a list of the one-hot encoded column names
label_columns = [label for label in all_labels if label != 'No Finding']

import os
print(f"Current working directory: {os.getcwd()}")

# Create a mapping of filename to its full path by searching recursively
print("Finding all images in xray_dataset... This might take a moment.")
image_path_map = {}
for root, dirs, files in os.walk(XRAY_DATASET_ROOT):
    for file in files:
        if file.endswith('.png'):
            image_path_map[file] = os.path.join(root, file)

# Check if image files exist in our map and assign full path
df['Full Path'] = df['Image Index'].map(image_path_map)
df['Image Exists'] = df['Full Path'].notna()

print(f"Total images found in mapping: {len(image_path_map)}")
print(df['Image Exists'].value_counts())

# Filter out missing images
df = df[df['Image Exists'] == True]

# Use a sample size of 10,000 (or max available)
target_sample_size = 30000
df = df.sample(n=min(target_sample_size, len(df)), random_state=42)

# Split the data into training and testing sets
train_df, test_df = train_test_split(df, test_size=0.3, random_state=42)

print(f"Number of training samples: {len(train_df)}")
print(f"Number of testing samples: {len(test_df)}")

# Create image data generators
train_datagen = ImageDataGenerator(
    shear_range=0.2,
    zoom_range=0.2,
    horizontal_flip=True
)

test_datagen = ImageDataGenerator()

# Use 'Full Path' and directory=None to allow absolute paths in the generator
train_generator = train_datagen.flow_from_dataframe(
    dataframe=train_df,
    directory=None,
    x_col="Full Path",
    y_col=label_columns,
    target_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="raw"
)

test_generator = test_datagen.flow_from_dataframe(
    dataframe=test_df,
    directory=None,
    x_col="Full Path",
    y_col=label_columns,
    target_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="raw"
)

# Create the model
base_model = EfficientNetB0(weights='imagenet', include_top=False, input_shape=(*IMAGE_SIZE, 3))

# Freeze the base model
base_model.trainable = False

# Add custom layers
x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(1024, activation='relu')(x)
predictions = Dense(len(label_columns), activation='sigmoid')(x)

model = Model(inputs=base_model.input, outputs=predictions)

# Compile the model
model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['binary_accuracy'])

model.summary()

# Training or Loading the model
MODEL_PATH = 'disease_model.keras'

if os.path.exists(MODEL_PATH):
    print(f"\nExisting model found at {MODEL_PATH}. Loading model...")
    model = tf.keras.models.load_model(MODEL_PATH)
else:
    print("\nNo existing model found. Starting training...")
    # Train the model
    try:
        history = model.fit(
            train_generator,
            steps_per_epoch=len(train_generator),
            epochs=3,
            validation_data=test_generator,
            validation_steps=len(test_generator)
        )

        # Evaluate the model
        loss, accuracy = model.evaluate(test_generator)
        print(f"Test Loss: {loss}")
        print(f"Test Accuracy: {accuracy}")

        if accuracy >= 0.92:
            print("Model achieved the target accuracy of 92% or higher.")
        else:
            print("Model did not achieve the target accuracy. Consider using a larger model or more epochs.")
        
        # Save the model
        model.save(MODEL_PATH)
        print(f"Model saved as {MODEL_PATH}")

    except FileNotFoundError as e:
        print(f"Error during training: {e}")
        print("Please ensure that the image files are in the correct directory and that the file paths in the CSV are correct.")

