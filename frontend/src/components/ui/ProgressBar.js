const ProgressBar = ({
   className="",
   text="",
   value=0,
   ...props
}) => {
   return (
      <div className={`progress ${className}`} role="progressbar"  style={{height: '40px'}} aria-valuenow={value} aria-valuemin="0" aria-valuemax="100">
         <div class="progress-bar" style={{ width: `${value}%`, backgroundColor: 'black' }}>{text}</div>
      </div>   
   );
};

export default ProgressBar;