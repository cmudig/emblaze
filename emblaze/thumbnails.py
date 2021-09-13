import json
import numpy as np
import pandas as pd
from io import BytesIO
from PIL import Image
import base64
from .datasets import ColumnarData
from .utils import Field, standardize_json

class Thumbnails:
    """
    Defines a set of data suitable for displaying info about points visualized
    in an embedding set.
    """
    def __init__(self, thumbnail_format):
        self.format = thumbnail_format

    def to_json(self):
        """
        Converts this set of thumbnails into a JSON object.
        """
        return {
            "format": self.format
        }
        
class TextThumbnails(Thumbnails):
    """
    Defines a set of textual thumbnails.
    """
    def __init__(self, names, descriptions=None, ids=None):
        """
        names: String values corresponding to a name for each point in the
            dataset.
        descriptions: Optional longer string descriptions for each point in the
            dataset.
        ids: If not None, a list of IDs that these thumbnails correspond to.
            If not provided, the IDs are assumed to be zero-indexed ascending
            integers.
        """
        super().__init__("text_descriptions")
        self.data = ColumnarData({
            Field.NAME: names
        }, ids)
        if descriptions is not None:
            self.data.set_field(Field.DESCRIPTION, descriptions)

    def name(self, ids=None):
        """
        Returns the name(s) for the given set of IDs, or all points if
        ids is not provided.
        """
        return self.data.field(Field.NAME, ids=ids)
    
    def description(self, ids=None):
        """
        Returns the description(s) for the given set of IDs, or all points if
        ids is not provided. Returns None if descriptions are not present.
        """
        return self.data.field(Field.DESCRIPTION, ids=ids)
        
    def to_json(self):
        result = super().to_json()
        names = self.data.field(Field.NAME)
        descriptions = self.data.field(Field.DESCRIPTION)
        result["items"] = {
            id_val: {
                "id": id_val,
                "name": str(names[i]),
                "description": str(descriptions[i]) if descriptions is not None else "",
                "frames": {} # Not implemented
            } for i, id_val in enumerate(self.data.ids)
        }
        return standardize_json(result)
    
    @staticmethod
    def from_json(data, ids=None):
        """
        Builds a TextThumbnails object from a JSON object. The provided object should
        have an "items" key with a dictionary mapping ID values to text thumbnail
        objects, each of which must have a 'name' and optionally 'description' keys.
        """
        assert "items" in data, "JSON object must contain an 'items' field"
        items = data["items"]
        if ids is None:
            try:
                ids = [int(id_val) for id_val in list(items.keys())]
                items = {int(k): v for k, v in items.items()}
            except:
                ids = list(items.keys())
            ids = sorted(ids)
        names = [items[id_val]["name"] for id_val in ids]
        descriptions = [items[id_val].get("description", "") for id_val in ids]
        return TextThumbnails(names, descriptions, ids)
   
    def __getitem__(self, ids):
        """
        Returns text thumbnail information for the given IDs.
        """
        if isinstance(ids, (list, np.ndarray, set)):
            return [self[id_val] for id_val in ids]
        else:
            result = { "name": self.data.field(Field.NAME, ids) }
            if self.data.has_field(Field.DESCRIPTION):
                result["description"] = self.data.field(Field.DESCRIPTION, ids)
            return result
    
MAX_IMAGE_DIM = 100
MAX_SPRITESHEET_DIM = 1000
 
class ImageThumbnails(Thumbnails):
    """
    Defines a set of image thumbnails. All thumbnails are scaled to the same
    dimensions to fit in a set of spritesheets.
    """
    def __init__(self, images, spritesheets=None, ids=None, grid_dimensions=None, image_size=None, names=None, descriptions=None):
        """
        Args:
            images: An array of images, each represented as a numpy array. The
                images contained can be different sizes if the images object is
                provided as a list.
            spritesheets: If provided, ignores the other spritesheet-generating
                parameters and initializes the thumbnails object with previously
                generated spritesheets.
            ids: The IDs of the points to which each image belongs. If none, this
                is assumed to be a zero-indexed increasing index.
            grid_dimensions: Number of images per spritesheet, defined as
                (images per row, images per column). If this is not provided,
                it will be inferred to make the spritesheets a reasonable size.
            image_size: Number of pixels per image, defined as (rows, cols).
                If this is not defined, images will be resized to a maximum of
                MAX_IMAGE_DIM x MAX_IMAGE_DIM, maintaining aspect ratio if all
                images are the same size.
            names: If provided, adds text names to each point. Names are assumed
                to be in the same order as images.
            descriptions: Similar to names, but these descriptions may be longer
                and only show on the currently selected point(s).
        """
        super().__init__("spritesheet")
        if spritesheets is not None:
            self.ids = ImageThumbnails._get_spritesheet_ids(spritesheets)
            self.spritesheets = spritesheets
            self.images = None
        else:
            self.images = images
            self.ids = ids or np.arange(len(images))
            self.make_spritesheets(images, self.ids, grid_dimensions, image_size)
        self._id_index = {id: i for i, id in enumerate(self.ids)}
        
        if names is not None:
            self.text_data = ColumnarData({
                Field.NAME: names
            }, ids)
            if descriptions is not None:
                self.text_data.set_field(Field.DESCRIPTION, descriptions)
        elif descriptions is not None:
            self.text_data = ColumnarData({
                Field.DESCRIPTION: descriptions
            }, ids)
        else:
            self.text_data = None
        
    def __getitem__(self, ids):
        """
        Returns image/text thumbnail information for the given IDs.
        """
        if isinstance(ids, (list, np.ndarray, set)):
            return [self[id_val] for id_val in ids]
        else:
            result = {}
            result["image"] = self.image(ids)
            if self.text_data is not None:
                result["name"] = self.text_data.field(Field.NAME, ids)
                if self.text_data.has_field(Field.DESCRIPTION):
                    result["description"] = self.text_data.field(Field.DESCRIPTION, ids)
            return result

    def image(self, ids=None):
        """
        Returns the image(s) for the given ID or set of IDs, or all points if ids
        is not provided.
        """
        if self.images is None:
            self.images = self._make_raw_images()
            
        if isinstance(ids, (list, np.ndarray, set)):
            index = [self._id_index[int(id_val)] for id_val in ids]
        else:
            index = self._id_index[int(ids)]

        return self.images[index]     
        
    def name(self, ids=None):
        """
        Returns the name(s) for the given set of IDs, or all points if
        ids is not provided. Returns None if names are not available.
        """
        if self.text_data is None: return None
        return self.text_data.field(Field.NAME, ids=ids)
    
    def description(self, ids=None):
        """
        Returns the description(s) for the given set of IDs, or all points if
        ids is not provided. Returns None if descriptions are not present.
        """
        if self.text_data is None: return None
        return self.text_data.field(Field.DESCRIPTION, ids=ids)
        
    def to_json(self):
        result = super().to_json()
        result["spritesheets"] = self.spritesheets
        if self.text_data is not None:
            names = self.text_data.field(Field.NAME)
            descriptions = self.text_data.field(Field.DESCRIPTION)
            result["items"] = {
                id_val: {
                    "id": id_val,
                    "name": str(names[i]) if names is not None else "",
                    "description": str(descriptions[i]) if descriptions is not None else "",
                    "frames": {} # Not implemented
                } for i, id_val in enumerate(self.text_data.ids)
            }

        return standardize_json(result)
    
    @staticmethod
    def from_json(data, ids=None):
        """
        Builds an ImageThumbnails object from a JSON object. The provided object should
        have a "spritesheets" object that defines PIXI spritesheets, and an
        optional "items" key that contains text thumbnails (see TextThumbnails
        for more information about the "items" field).
        """
        assert "spritesheets" in data, "JSON object must contain a 'spritesheets' field"
        spritesheets = data["spritesheets"]
        if ids is None:
            ids = ImageThumbnails._get_spritesheet_ids(spritesheets)
            
        names = None
        descriptions = None
        if "items" in data:
            items = data["items"]
            names = [items[id_val]["name"] for id_val in ids]
            descriptions = [items[id_val].get("description", "") for id_val in ids]

        return ImageThumbnails(None,
                               spritesheets=spritesheets,
                               ids=ids,
                               names=names,
                               descriptions=descriptions)

    @staticmethod
    def _get_spritesheet_ids(spritesheets):
        ids = sorted([k for sp in spritesheets.values() for k in sp["spec"]["frames"].keys()])
        try:
            ids = [int(id_val) for id_val in ids]
        except:
            pass
        ids = sorted(ids)
        return np.array(ids)
        
    def _make_raw_images(self):
        """
        Regenerates and returns the original images matrix based on self.spritesheets
        and self.ids.
        """
        assert len(self.spritesheets), "spritesheets is empty"
        random_spec = self.spritesheets[list(self.spritesheets.keys())[0]]["spec"]["frames"]
        random_frame = random_spec[list(random_spec.keys())[0]]["frame"]
        cols = random_frame["w"]
        rows = random_frame["h"]
        
        result = np.zeros((len(self.ids), rows, cols, 4), dtype=np.uint8)
        seen_ids = set()
        for key, spritesheet in self.spritesheets.items():
            buffer = BytesIO(base64.b64decode(spritesheet["image"].encode('ascii')))
            img = np.array(Image.open(buffer, formats=('PNG',)))
            
            for id_val, image_spec in spritesheet["spec"]["frames"].items():
                frame = image_spec["frame"]
                result[self._id_index[int(id_val)]] = img[frame["y"]:frame["y"] + frame["h"],
                                                          frame["x"]:frame["x"] + frame["w"]]
                seen_ids.add(int(id_val))
        if len(seen_ids & set(self.ids.tolist())) != len(self.ids):
            print("missing ids when loading images from spritesheets:", set(self.ids.tolist()) - seen_ids)
        return result
        
    def make_spritesheets(self, images, ids, grid_dimensions=None, image_size=None):
        """
        Generates a set of spritesheets from the given image data.
        
        Args:
            data: A ColumnarData object that contains a single field _images.
            grid_dimensions: Number of images per spritesheet, defined as
                (images per row, images per column)
            image_size: Number of pixels per image, defined as (rows, cols)
        """
        
        image_size = image_size or self._compute_image_size(images)
        grid_dimensions = grid_dimensions or self._compute_grid_dimensions(image_size)
        
        spritesheets = {}
        current_spritesheet = None

        current_image = None
        image_index = 0
        image_encoding_warning = False
        for i in range(len(images)):
            if i % (grid_dimensions[0] * grid_dimensions[1]) == 0:
                if current_image is not None and current_spritesheet is not None:
                    img = Image.fromarray(current_image, 'RGBA')
                    with BytesIO() as output:
                        img.save(output, format='png')
                        contents = output.getvalue()
                    current_spritesheet["image"] = base64.b64encode(contents).decode('ascii')
                    current_spritesheet["imageFormat"] = "image/png"
                    image_index += 1
                    
                current_spritesheet = {
                    "spec": {
                        "meta": {
                            "image": "img_{}.png".format(image_index),
                            "size": {
                                "w": grid_dimensions[1] * image_size[1],
                                "h": grid_dimensions[0] * image_size[0]},
                            "format": "RGBA8888"
                        },
                        "frames": {}
                    }
                }
                spritesheets["img_{}.json".format(image_index)] = current_spritesheet

                current_image = np.zeros((image_size[0] * grid_dimensions[0], image_size[1] * grid_dimensions[1], 4), dtype=np.uint8)
                
            relative_i = i % (grid_dimensions[0] * grid_dimensions[1])
            pos = (relative_i // grid_dimensions[1] * image_size[0], relative_i % grid_dimensions[1] * image_size[1])
            
            # First validate the image
            image = images[i]
            assert len(image.shape) == 3, "Images must be 3-dimensional arrays (include a color channel)"
            image = self._standardize_image_format(image, image.shape[:2])
            if np.max(image[:,:,:3]) < 2 and not image_encoding_warning:
                print("Warning: Your image pixel values are very small. ImageThumbnails uses integer pixel values from 0-255.")
                image_encoding_warning = True
            
            # Resize the image if necessary
            if tuple(image.shape[:2]) != image_size:
                resized_image = Image.fromarray(image).resize((image_size[1], image_size[0]))
                image = np.array(resized_image)
                assert image.shape == (*image_size, 4), "Incorrect resize shape! Something weird happened."
                
            # Place the image
            current_image[pos[0]:pos[0] + image_size[0], pos[1]:pos[1] + image_size[1],:] = image
            
            current_spritesheet["spec"]["frames"][str(i)] = {
                "frame": {
                    "x": pos[1],
                    "y": pos[0],
                    "w": image_size[1],
                    "h": image_size[0]
                },
                "rotated": False,
                "trimmed": False
            }

        img = Image.fromarray(current_image, 'RGBA')
        with BytesIO() as output:
            img.save(output, format='png')
            contents = output.getvalue()
        current_spritesheet["image"] = base64.b64encode(contents).decode('ascii')
        current_spritesheet["imageFormat"] = "image/png"
        
        self.spritesheets = spritesheets
        
    def _standardize_image_format(self, image, image_size):
        """
        Converts the given image array to RGBA uint8 format.
        
        Args:
            image: An image matrix.
            image_size: The size of the image in (rows, cols).
        """
        image = image.astype(np.uint8)
        result = np.zeros((image_size[0], image_size[1], 4), dtype=np.uint8)
        if image.shape[2] == 1:
            for channel in range(3):
                result[:,:,channel] = image[:,:,0]
            result[:,:,3] = 255
        elif image.shape[2] == 3:
            result[:,:,:3] = image
            result[:,:,3] = 255
        elif image.shape[2] == 4:
            result = image
        else:
            raise ValueError("Incorrect image shape, expected 3rd dimension to be 1, 3 or 4; got {} instead".format(image.shape[2]))
        return result
        
    def _compute_image_size(self, images):
        """
        Computes a reasonable image size to rescale all images to.
        """
        if len(images) == 0: return (0, 0)
        test_dim = images[0].shape[:2]
        if all(img.shape[:2] == test_dim for img in images):
            if max(*test_dim) < MAX_IMAGE_DIM:
                # The images are already a reasonable size
                return test_dim
            
            # Resize preserving aspect ratio
            scale = min(MAX_IMAGE_DIM / test_dim[0], MAX_IMAGE_DIM / test_dim[1])
            return (int(test_dim[0] * scale), int(test_dim[1] * scale))
        else:
            # Get the average aspect ratio and choose a dimension so that no
            # image is scaled up
            aspect = np.mean([img.shape[0] / img.shape[1] for img in images])
            if aspect < 1.0:
                min_dim = min(MAX_IMAGE_DIM, np.min(np.array([img.shape[1] for img in images])))
                return (int(min_dim * aspect), int(min_dim))
            else:
                min_dim = min(MAX_IMAGE_DIM, np.min(np.array([img.shape[0] for img in images])))
                return (int(min_dim), int(min_dim / aspect))
        
    def _compute_grid_dimensions(self, image_size):
        """
        Computes a reasonable number of images per side of the spritesheet.
        """
        return (MAX_SPRITESHEET_DIM // image_size[0], MAX_SPRITESHEET_DIM // image_size[1])