import json
from typing import Text
import numpy as np
import pandas as pd
from io import BytesIO
from PIL import Image
import base64
import copy
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
        
    @classmethod
    def from_json(cls, data, ids=None):
        """
        Loads this Thumbnails object from JSON. This base method chooses the
        appropriate Thumbnails subclass to initialize, based on the format
        declared in the given JSON object data. The ids parameter can be used
        to subset the point IDs that are loaded from the file.
        """
        if data["format"] == "spritesheet_and_text":
            return CombinedThumbnails.from_json(data)
        elif data["format"] == "spritesheet":
            return ImageThumbnails.from_json(data, ids=ids)
        elif data["format"] == "text_descriptions":
            return TextThumbnails.from_json(data, ids=ids)
        raise ValueError("Unsupported data format '{}'".format(data["format"]))
        
    def get_ids(self):
        """Return a numpy array of the IDs used in this thumbnails object."""
        raise NotImplementedError
    
    def save(self, file_path_or_buffer):
        """
        Save this Thumbnails object to the given file path or file-like object
        (in JSON format).
        """
        if isinstance(file_path_or_buffer, str):
            # File path
            with open(file_path_or_buffer, 'w') as file:
                json.dump(self.to_json(), file)
        else:
            # File object
            json.dump(self.to_json(), file_path_or_buffer)
            
    @classmethod
    def load(cls, file_path_or_buffer, ids=None):
        """
        Load the appropriate Thumbnails subclass from the given file path or
        file-like object containing JSON data.
        """
        if isinstance(file_path_or_buffer, str):
            # File path
            with open(file_path_or_buffer, 'r') as file:
                return cls.from_json(json.load(file), ids=ids)
        else:
            # File object
            return cls.from_json(json.load(file_path_or_buffer), ids=ids)
        
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
        if ids is not None:
            assert len(names) == len(ids), "Length mismatch: got {} names for {} IDs".format(len(names), len(ids))
            if descriptions is not None:
                assert len(descriptions) == len(ids), "Length mismatch: got {} descriptions for {} IDs".format(len(descriptions), len(ids))
        self.data = ColumnarData({
            Field.NAME: names
        }, ids)
        if descriptions is not None:
            self.data.set_field(Field.DESCRIPTION, descriptions)

    def get_ids(self):
        return self.data.ids
    
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
        def _make_json_item(i, id_val):
            item = {"id": id_val, "name": str(names[i])}
            if descriptions is not None and descriptions[i]:
                item["description"] = str(descriptions[i])
            return item
        result["items"] = {
            id_val: _make_json_item(i, id_val)
            for i, id_val in enumerate(self.data.ids)
            if names[i] or (descriptions is not None and descriptions[i])
        }
        return standardize_json(result)
    
    @classmethod
    def from_json(cls, data, ids=None):
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
        return cls(names, descriptions, ids)
   
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
            self.ids = ids if ids is not None else np.arange(len(images))
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
        
    def get_ids(self):
        return self.ids
        
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
            index = [self._id_index.get(int(id_val), None) for id_val in ids]
            return [self.images[i] if i is not None else None for i in index]
        else:
            index = self._id_index.get(int(ids), None)
            if index is not None:
                return self.images[index] 
            return None
        
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
        
    def get_spritesheets(self):
        return self.spritesheets
    
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
                } for i, id_val in enumerate(self.text_data.ids) if names[i] or descriptions[i]
            }

        return standardize_json(result)
    
    @classmethod
    def from_json(cls, data, ids=None):
        """
        Builds an ImageThumbnails object from a JSON object. The provided object should
        have a "spritesheets" object that defines PIXI spritesheets, and an
        optional "items" key that contains text thumbnails (see TextThumbnails
        for more information about the "items" field).
        """
        assert "spritesheets" in data, "JSON object must contain a 'spritesheets' field"
        spritesheets = data["spritesheets"]
        if ids is None:
            ids = cls._get_spritesheet_ids(spritesheets)
            
        names = None
        descriptions = None
        if "items" in data:
            items = data["items"]
            names = [items[str(id_val)]["name"] for id_val in ids]
            descriptions = [items[str(id_val)].get("description", "") for id_val in ids]

        return cls(None,
                   spritesheets=spritesheets,
                   ids=ids,
                   names=names,
                   descriptions=descriptions)

    @classmethod
    def _get_spritesheet_ids(cls, spritesheets):
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
            images: A matrix or list of images in RGBA format (e.g. shape = rows x cols x 4).
            ids: The point IDs to associate with each image.
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
        assert len(ids) == len(images), "Number of IDs provided must be equal to number of images"
        for i, id_val in enumerate(ids):
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
            
            current_spritesheet["spec"]["frames"][str(id_val)] = {
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
    
    
class CombinedThumbnails(Thumbnails):
    """
    A class representing a combination of images and/or text thumbnails. The
    thumbnail objects that are merged may have overlapping IDs, but they may not
    have overlapping IDs for the same thumbnail type. For example, two
    ImageThumbnails objects cannot both have images for the same point ID.
    """
    def __init__(self, thumbnail_objects):
        has_images = any(t.format == "spritesheet" for t in thumbnail_objects)
        has_texts = any(t.format == "text_descriptions" for t in thumbnail_objects)
        super().__init__(("spritesheet_and_text" if has_images else "text_descriptions") if has_texts else "spritesheet")
        
        # Merge the list of representations together
        self.ids = np.array(sorted(set.union(*(set(t.get_ids().tolist()) for t in thumbnail_objects))))
        self._id_index = {id_val: i for i, id_val in enumerate(self.ids)}
        
        names = None
        descriptions = None
        spritesheets = {}
        seen_images = set()
        seen_texts = set()
        for t, thumbnails in enumerate(thumbnail_objects):
            indexes = [self._id_index[id_val] for id_val in thumbnails.get_ids()]
            
            if thumbnails.format == "spritesheet":
                assert not set(thumbnails.get_ids().tolist()) & seen_images, "Overlapping image thumbnails"
                for spritesheet_name, value in thumbnails.get_spritesheets().items():
                    new_spritesheet_name = str(t) + "_" + spritesheet_name
                    spritesheet = copy.deepcopy(value)
                    spritesheet["spec"]["meta"]["image"] = str(t) + "_" + spritesheet["spec"]["meta"]["image"]
                    spritesheets[new_spritesheet_name] = spritesheet
                seen_images |= set(thumbnails.get_ids().tolist())
            
            if thumbnails.format == "text_descriptions" or (thumbnails.format == "spritesheet" and thumbnails.name() is not None):
                assert not set(thumbnails.get_ids().tolist()) & seen_texts, "Overlapping text thumbnails"
                seen_texts |= set(thumbnails.get_ids().tolist())
            
            nm = thumbnails.name()
            if nm is not None:
                if names is None: names = np.empty(len(self.ids), dtype='O')
                names[indexes] = thumbnails.name()
            desc = thumbnails.description()
            if desc is not None:
                if descriptions is None: descriptions = np.empty(len(self.ids), dtype='O')
                descriptions[indexes] = desc
            
        # Store an internal ImageThumbnails and a TextThumbnails object
        self.image_thumbnails = ImageThumbnails(None, spritesheets=spritesheets) if spritesheets else None
        self.text_thumbnails = TextThumbnails(names, descriptions, ids=self.ids) if names is not None else None
        
    def get_ids(self):
        return self.ids

    def get_spritesheets(self):
        return self.image_thumbnails.spritesheets if self.image_thumbnails else None
    
    def to_json(self):
        result = super().to_json()
        
        if self.image_thumbnails is not None:
            result["spritesheets"] = self.image_thumbnails.to_json()["spritesheets"]
        if self.text_thumbnails is not None:
            result["items"] = self.text_thumbnails.to_json()["items"]
            
        return result
    
    @classmethod
    def from_json(cls, data, ids=None):
        thumbnails = []
        if "spritesheets" in data:
            thumbnails.append(ImageThumbnails.from_json({"spritesheets": data["spritesheets"]}))
            
        if "items" in data:
            thumbnails.append(TextThumbnails.from_json({"items": data["items"]}))
            
        return cls(thumbnails)
    
    def image(self, ids=None):
        """
        Returns the image(s) for the given ID or set of IDs, or all points if ids
        is not provided.
        """
        return self.image_thumbnails.image(ids=ids) if self.image_thumbnails else None
        
    def name(self, ids=None):
        """
        Returns the name(s) for the given set of IDs, or all points if
        ids is not provided. Returns None if names are not available.
        """
        return self.text_thumbnails.name(ids=ids) if self.text_thumbnails else None
    
    def description(self, ids=None):
        """
        Returns the description(s) for the given set of IDs, or all points if
        ids is not provided. Returns None if descriptions are not present.
        """
        return self.text_thumbnails.description(ids=ids) if self.text_thumbnails else None
        