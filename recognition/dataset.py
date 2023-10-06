import os
import torch
from torch.utils.data import Dataset
from torchvision import transforms
from PIL import Image
import matplotlib.pyplot as plt

class Normalise(object):
    """Normalises the brain region of the image."""
    def __call__(self, sample):
        image, mask = sample['image'], sample['mask']
        # Ensuring the channel dimension is not in the first position
        brain_pixels = image.numpy()[0, mask.numpy() > 0] 

        mean = brain_pixels.mean()
        std = brain_pixels.std()
        Normalised_image = (image - mean) / std
        return {'image': normalised_image, 'mask': mask}

class ClipAndRescale(object):
    """Clips and rescales the image, and sets the non-brain region to 0."""
    def __init__(self, clip_range=(-5, 5), rescale_range=(0, 1)):
        self.clip_range = clip_range
        self.rescale_range = rescale_range

    def __call__(self, sample):
        image, mask = sample['image'], sample['mask']

        # Clip values
        clipped_image = torch.clamp(image, *self.clip_range)
        
        # Rescale to [0,1]
        """ maps the minimum value of clip_range to the minimum of rescale_range and the maximum of clip_range to the maximum of rescale_range. """
        min_val, max_val = self.rescale_range
        rescaled_image = (clipped_image - self.clip_range[0]) / \
                         (self.clip_range[1] - self.clip_range[0]) * \
                         (max_val - min_val) + min_val
        
        # Ensuring the mask has the same shape as the image tensor before using it for indexing
        """ Adds an additional dimension at the start, changing the shape of the mask from (H, W) to (1, H, W), assuming the original mask is 2D. This is needed to match the 3D shape of the image (C, H, W) """
        expanded_mask = mask.unsqueeze(0).expand_as(rescaled_image)
        
        # Setting the non-brain region to 0
        rescaled_image[expanded_mask == 0] = 0

        return {'image': rescaled_image, 'mask': mask}

class Rescale(object):
    """Rescales the image and mask to the specified size."""
    def __init__(self, output_size):
        assert isinstance(output_size, (int, tuple))
        self.output_size = output_size

    def __call__(self, sample):
        image, mask = sample['image'], sample['mask']
        """ Rescales the image using bilinear interpolation, which is suitable for image data because it performs interpolation between pixel values, providing a smoother transition when resizing """
        image = image.resize(self.output_size, Image.BILINEAR)
        """ Rescales the mask using nearest-neighbor interpolation, ensuring that mask values remain discrete and preventing the introduction of new label values, which is critical for categorical data like segmentation masks """
        mask = mask.resize(self.output_size, Image.NEAREST)
        return {'image': image, 'mask': mask}

class ToTensor(object):
    """Converts the image and mask to PyTorch tensors."""
    def __call__(self, sample):
        image, mask = sample['image'], sample['mask']
        image = transforms.functional.to_tensor(image)
        mask = transforms.functional.to_tensor(mask).squeeze()
        return {'image': image, 'mask': mask}

def get_transform():
    """Combines the Rescale, ToTensor, Normalise, and ClipAndRescale transformations into one."""
    return transforms.Compose([
        Rescale((128, 128)),
        ToTensor(),
        Normalise(),
        ClipAndRescale(),
    ])

class ISICDataset(Dataset):
    """ISIC Dataset class for loading and preprocessing data."""
    def __init__(self, dataset_type, transform=None):
        assert dataset_type in ['training', 'validation', 'test'], "Invalid dataset type. Must be one of ['training', 'validation', 'test']"
        self.root_dir = os.path.join('../../Data', dataset_type) 
        self.transform = transform

        """ sort by masks and lesion images """
        self.image_list = sorted([f for f in os.listdir(self.root_dir) if f.endswith('.jpg')])
        self.mask_list = [f.replace('.jpg', '_superpixels.png') for f in self.image_list]

    def __len__(self):
        return len(self.image_list)

    def __getitem__(self, idx):
        """ file names """
        img_name = os.path.join(self.root_dir, self.image_list[idx])
        mask_name = os.path.join(self.root_dir, self.mask_list[idx])

        """ RGB image, greyscale mask """
        image = Image.open(img_name).convert('RGB')
        mask = Image.open(mask_name).convert('L')
        sample = {'image': image, 'mask': mask}
        if self.transform:
            sample = self.transform(sample)
        return sample

if __name__ == "__main__":
    # Loading the training, validation, and test datasets
    train_dataset = ISICDataset(dataset_type='training', transform=get_transform())
    val_dataset = ISICDataset(dataset_type='validation', transform=get_transform())
    test_dataset = ISICDataset(dataset_type='test', transform=get_transform())

    # Example to print the size of images and masks from the training dataset
    for i in range(len(train_dataset)):
        sample = train_dataset[i]
        print(i, sample['image'].size(), sample['mask'].size())
        if i == 3:
            break

    # Example to visualise original and transformed images and masks
    fig, ax = plt.subplots(nrows=4, ncols=2, figsize=(12, 12))
    
    # Load an example from the dataset
    example_idx = 0
    example_original = ISICDataset(dataset_type='training')[example_idx]
    example_transformed = train_dataset[example_idx]

    # Plot original image and mask
    ax[0, 0].imshow(example_original['image'])
    ax[0, 0].set_title('Original Image')
    ax[0, 1].imshow(example_original['mask'], cmap='gray')
    ax[0, 1].set_title('Original Mask')
    
    # Plot transformed image and mask
    ax[1, 0].imshow(example_transformed['image'].numpy().transpose(1, 2, 0))
    ax[1, 0].set_title('Transformed Image')
    ax[1, 1].imshow(example_transformed['mask'].numpy(), cmap='gray')
    ax[1, 1].set_title('Transformed Mask')
    
    plt.tight_layout()
    plt.show()
