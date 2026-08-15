'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');

class FakeNode {
  constructor(name) { this.name=name; this.children=[]; this.attributes={}; this.style={}; this.parent=null; this.textContent=''; }
  setAttribute(name,value){this.attributes[name]=String(value)}
  append(...nodes){for(const node of nodes){node.parent=this;this.children.push(node)}}
  replaceChildren(){this.children=[]}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter((node)=>node!==this)}
  getBoundingClientRect(){
    const lines=this.children.length?this.children.map((child)=>String(child.textContent)): [String(this.textContent)];
    const font=(Number.parseFloat(this.style.fontSize)||10)*document.displayScale;
    const width=Math.max(...lines.map((line)=>line.length),0)*font*.58,height=Math.max(1,lines.length)*font*1.08;
    const x=(Number(this.attributes.x)||0)*document.displayScale,y=(Number(this.attributes.y)||0)*document.displayScale;
    return {left:x-width/2,right:x+width/2,top:y-height/2,bottom:y+height/2,width,height};
  }
}

global.window=global;
global.document={displayScale:1,createElementNS(_namespace,name){return new FakeNode(name)}};
require(path.join(__dirname,'..','public','polygon-labels.js'));
const engine=global.WorkbenchPolygonLabels,identity=(point)=>point;
const polygon=(coordinates)=>({type:'Feature',geometry:{type:'Polygon',coordinates}});
const square=(x=0,y=0,size=20)=>polygon([[[x,y],[x+size,y],[x+size,y+size],[x,y+size],[x,y]]]);

const dense=square(0,0,20),densePoint=engine.interiorPoint(dense,identity);
assert(densePoint.radius>9&&densePoint.radius<=10.1,'square uses a largest-inscribed interior position');
const holed=polygon([[[0,0],[30,0],[30,30],[0,30],[0,0]],[[9,9],[21,9],[21,21],[9,21],[9,9]]]);
const holePoint=engine.interiorPoint(holed,identity);
assert(holePoint.radius>0&&!(holePoint.x>9&&holePoint.x<21&&holePoint.y>9&&holePoint.y<21),'hole is excluded from label interiors');
const multipart={type:'Feature',geometry:{type:'MultiPolygon',coordinates:[[[[0,0],[4,0],[4,4],[0,4],[0,0]]],[[[20,0],[40,0],[40,20],[20,20],[20,0]]]]}};
const multipartPoint=engine.interiorPoint(multipart,identity);
assert(multipartPoint.x>20&&multipartPoint.radius>8,'multipart labels use the roomiest polygon');
assert.equal(engine.shortenLocality('City of Richmond'),'Richmond');
assert.equal(engine.shortenLocality('Henrico County'),'Henrico');

function layout(entries,{scale=1,maxLabels=20}={}){
  document.displayScale=scale;const group=new FakeNode('g');
  const accepted=engine.layout({group,entries,view:{x:0,y:0,width:100,height:100},viewport:{width:100*scale,height:100*scale},project:identity,pathFor:()=> 'M0 0Z',minFontPx:8,maxFontPx:14,maxLabels});
  return {accepted,group};
}

const simplified=layout([{id:'simple',feature:square(20,20,40),priority:1,candidates:[["A locality label that is deliberately much too long"],["Short"]]}]);
assert.equal(simplified.accepted.length,1);
assert.equal(simplified.accepted[0].text.children[0].textContent,'Short','candidate simplification is deterministic');
assert.equal(simplified.group.children[0].name,'clipPath','accepted labels are clipped to their polygon');
const hidden=layout([{id:'narrow',feature:square(0,0,8),priority:1,candidates:[["12345678901234567890"]]}]);
assert.equal(hidden.accepted.length,0,'an exact Bzone identifier is hidden instead of truncated');
const collision=layout([
  {id:'selected',feature:square(20,20,50),priority:30,candidates:[["Selected"]]},
  {id:'considered',feature:square(20,20,50),priority:20,candidates:[["Considered"]]},
  {id:'remaining',feature:square(20,20,50),priority:0,candidates:[["Remaining"]]},
]);
assert.deepEqual(collision.accepted.map((item)=>item.entry.id),['selected'],'measured collision rejection preserves priority order');
assert.equal(layout(Array.from({length:5},(_,index)=>({id:String(index),feature:square(index*18,60,16),priority:0,candidates:[[String(index)]]})),{maxLabels:2}).accepted.length,2,'label cap is enforced');
for(const scale of [1,1.25,1.5])assert.equal(layout([{id:'scaled',feature:square(10,10,40),priority:1,candidates:[["Scaled"]]}],{scale}).accepted.length,1,`display scale ${scale} relayout remains stable`);

console.log('polygon-labels deterministic tests passed');
