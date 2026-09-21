(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  root.WorkbenchHypercubeSummary=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  const FALLBACK_RUNTIME_MS=11*60*1000;

  function median(values){
    const ordered=(values||[]).filter(Number.isFinite).sort((a,b)=>a-b);
    if(!ordered.length)return NaN;
    const middle=Math.floor(ordered.length/2);
    return ordered.length%2?ordered[middle]:(ordered[middle-1]+ordered[middle])/2;
  }

  function estimateEta({successfulDurationsMs=[],activeElapsedMs=[],preparingCount=0,stoppingCount=0,waitingCount=0,concurrency=1,queuedBehind=false,fallbackRuntimeMs=FALLBACK_RUNTIME_MS}={}){
    const samples=successfulDurationsMs.filter((value)=>Number.isFinite(value)&&value>0).slice(0,25),measured=samples.length>=3;
    const perRunMs=measured?median(samples):fallbackRuntimeMs,slots=Math.max(1,Math.floor(Number(concurrency)||1)),loads=Array.from({length:slots},()=>0);
    const assign=(milliseconds)=>{let index=0;for(let candidate=1;candidate<loads.length;candidate+=1)if(loads[candidate]<loads[index])index=candidate;loads[index]+=milliseconds;};
    activeElapsedMs.forEach((elapsed)=>assign(Math.max(60*1000,perRunMs-(Number.isFinite(elapsed)?Math.max(0,elapsed):0))));
    for(let index=0;index<preparingCount;index+=1)assign(perRunMs);
    for(let index=0;index<stoppingCount;index+=1)assign(60*1000);
    for(let index=0;index<waitingCount;index+=1)assign(perRunMs);
    return{remainingMs:Math.max(0,...loads),perRunMs,sampleCount:samples.length,measured,slotCount:slots,queuedBehind:Boolean(queuedBehind)};
  }

  function timestamp(value){
    const result=new Date(value||'').getTime();
    return Number.isFinite(result)?result:NaN;
  }

  function elapsedRuntime({jobs=[],nowMs=Date.now()}={}){
    const activeStates=new Set(['preparing','running','exporting','stopping']),batches=new Map();
    (jobs||[]).forEach((job,index)=>{
      const key=String(job?.batchId||job?.batch?.id||job?.id||`job-${index}`);
      if(!batches.has(key))batches.set(key,[]);
      batches.get(key).push(job||{});
    });
    let elapsedMs=0,startedBatches=0,activeBatches=0;
    batches.forEach((batchJobs)=>{
      const latest=new Map();
      batchJobs.forEach((job,index)=>{
        const caseKey=job.baseline?'baseline':String(job.variationId||job.id||index),prior=latest.get(caseKey);
        if(!prior||timestamp(job.createdAt)>=timestamp(prior.createdAt))latest.set(caseKey,job);
      });
      batchJobs=[...latest.values()];
      const starts=batchJobs.map((job)=>timestamp(job.startedAt)).filter(Number.isFinite);
      if(!starts.length)return;
      const start=Math.min(...starts),active=batchJobs.some((job)=>activeStates.has(job.state));
      const finishes=batchJobs.map((job)=>timestamp(job.finishedAt)).filter(Number.isFinite);
      const end=active?Number(nowMs):(finishes.length?Math.max(...finishes):start);
      elapsedMs+=Math.max(0,Number.isFinite(end)?end-start:0);
      startedBatches+=1;
      if(active)activeBatches+=1;
    });
    return{elapsedMs,started:startedBatches>0,startedBatches,activeBatches};
  }

  return{FALLBACK_RUNTIME_MS,median,estimateEta,elapsedRuntime};
});
