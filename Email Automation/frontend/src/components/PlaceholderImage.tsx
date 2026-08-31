import React from 'react';

interface PlaceholderImageProps {
  size?: number;
  className?: string;
  alt?: string;
}

const PlaceholderImage: React.FC<PlaceholderImageProps> = ({ 
  size = 128, 
  className = "", 
  alt = "Placeholder image" 
}) => {
  // Create a simple SVG placeholder that scales with the size prop
  const svgData = `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="${size}" height="${size}" fill="#F3F4F6"/>
      <circle cx="${size/2}" cy="${size/2}" r="${size/5}" fill="#9B9BA7"/>
      <path d="M${size/2} ${size*0.7}C${size/2} ${size*0.7-size/5.3} ${size/2-size/5.3} ${size*0.7-size/5.3}S${size/2} ${size*0.7-size/5.3} ${size/2} ${size*0.7}" fill="#9B9BA7"/>
    </svg>
  `;

  const dataUri = `data:image/svg+xml;base64,${btoa(svgData)}`;

  return (
    <img 
      src={dataUri} 
      alt={alt} 
      className={className}
      width={size}
      height={size}
    />
  );
};

export default PlaceholderImage;
