import React from 'react';

const Flex = ({ 
   children, 
   direction = "row",       // row, column
   justify = "start",       // start, center, end, between, around
   align = "stretch",       // start, center, end, stretch
   wrap = false,           // true/false
   gap,                    // 0-5 или custom
   className = "",
   style = {},
   ...props
}) => {
   let flexClass = "d-flex";
  
   const directionClass = direction === "column" ? "flex-column" : "";
  
   const justifyClasses = {
      start: "justify-content-start",
      center: "justify-content-center", 
      end: "justify-content-end",
      between: "justify-content-between",
      around: "justify-content-around"
   };
  
   const alignClasses = {
      start: "align-items-start",
      center: "align-items-center",
      end: "align-items-end", 
      stretch: "align-items-stretch"
   };
  
   const wrapClass = wrap ? "flex-wrap" : "";

   const gapClass = gap ? `gap-${gap}` : "";

   const combinedClass = [
      flexClass,
      directionClass,
      justifyClasses[justify],
      alignClasses[align], 
      wrapClass,
      gapClass,
      className
   ].filter(Boolean).join(" ");

   return (
   <div 
      className={combinedClass}
      style={style}
      {...props}
   >
      {children}
   </div>
   );
};

export default Flex;