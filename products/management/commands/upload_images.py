import os
import logging
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from products.models import Product, ProductImage

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Bulk upload and process product images"

    def add_arguments(self, parser):
        parser.add_argument(
            '--image-dir',
            type=str,
            default='media/images/product_images',
            help='Directory containing product images'
        )
        parser.add_argument(
            '--max-images',
            type=int,
            default=5,
            help='Maximum number of images per product'
        )
        parser.add_argument(
            '--create-missing',
            action='store_true',
            help='Create ProductImage records for products without images'
        )

    def handle(self, *args, **options):
        image_dir = Path(settings.MEDIA_ROOT) / options['image_dir']
        max_images = options['max_images']
        create_missing = options['create_missing']

        if not image_dir.exists():
            self.stdout.write(self.style.ERROR(f"Image directory {image_dir} does not exist!"))
            return

        # Get all image files
        image_files = list(image_dir.glob('*'))
        if not image_files:
            self.stdout.write(self.style.WARNING("No image files found in directory!"))
            return

        # Process products
        for product in Product.objects.all():
            # Skip if product already has maximum images
            if product.images.count() >= max_images:
                continue

            # Find matching images
            matching_images = []
            for image_file in image_files:
                # Try to match filename with product name
                if product.name.lower() in image_file.stem.lower():
                    matching_images.append(image_file)

            # Sort images by modification time (newest first)
            matching_images.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Process matching images
            for i, image_file in enumerate(matching_images[:max_images]):
                try:
                    # Check if image already exists
                    existing_image = ProductImage.objects.filter(
                        product=product,
                        image=image_file.name
                    ).first()
                    
                    if not existing_image:
                        # Create new ProductImage
                        with image_file.open('rb') as f:
                            image = File(f)
                            product_image = ProductImage(
                                product=product,
                                image=image,
                                is_featured=i == 0,  # Make first image featured
                                alt_text=f"{product.name} image {i+1}"
                            )
                            product_image.save()
                            self.stdout.write(self.style.SUCCESS(
                                f"Added {image_file.name} to {product.name}"
                            ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"Image {image_file.name} already exists for {product.name}"
                        ))

                except Exception as e:
                    logger.error(f"Error processing {image_file.name}: {str(e)}")
                    self.stdout.write(self.style.ERROR(
                        f"Error processing {image_file.name}: {str(e)}"
                    ))

            # Create placeholder image if requested and no images found
            if create_missing and not product.images.exists():
                try:
                    # Create a placeholder image
                    placeholder_image = ProductImage(
                        product=product,
                        image='placeholder.jpg',
                        is_featured=True,
                        alt_text=f"Placeholder for {product.name}"
                    )
                    placeholder_image.save()
                    self.stdout.write(self.style.WARNING(
                        f"Created placeholder image for {product.name}"
                    ))
                except Exception as e:
                    logger.error(f"Error creating placeholder for {product.name}: {str(e)}")
                    self.stdout.write(self.style.ERROR(
                        f"Error creating placeholder for {product.name}: {str(e)}"
                    ))

        self.stdout.write(self.style.SUCCESS("Image processing completed!"))
