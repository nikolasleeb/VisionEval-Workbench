(function(global){
  'use strict';

  function polygons(geometry){
    if(geometry?.type==='Polygon')return [geometry.coordinates];
    if(geometry?.type==='MultiPolygon')return geometry.coordinates;
    return [];
  }

  function rgba(value,alpha=.76){
    const hex=String(value||'').trim().match(/^#([0-9a-f]{6})$/i);
    if(!hex)return [.14,.2,.27,alpha];
    const number=parseInt(hex[1],16);
    return [(number>>16&255)/255,(number>>8&255)/255,(number&255)/255,alpha];
  }

  function buildMesh(features,maplibregl,color='#243244'){
    const vertices=[],indices=[],lineColor=rgba(color),addSegment=(a,b,height)=>{
      const start=maplibregl.MercatorCoordinate.fromLngLat(a,height+3),end=maplibregl.MercatorCoordinate.fromLngLat(b,height+3),offset=indices.length;
      vertices.push(start.x,start.y,start.z,...lineColor,end.x,end.y,end.z,...lineColor);indices.push(offset,offset+1);
    };
    for(const feature of features||[]){
      const height=Number(feature?.properties?.__height)||0,decrease=feature?.properties?.__direction==='decrease';
      for(const polygon of polygons(feature?.geometry))for(const ring of polygon||[]){
        const points=(ring||[]).filter((point)=>Array.isArray(point)&&Number.isFinite(Number(point[0]))&&Number.isFinite(Number(point[1])));
        for(let index=0;index+1<points.length;index+=1){
          if(decrease&&index%2===1)continue;
          addSegment(points[index],points[index+1],height);
        }
      }
    }
    return {vertices:new Float32Array(vertices),indices:new Uint32Array(indices)};
  }

  function compile(gl,type,source){
    const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);
    if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(shader)||'Extrusion border shader compilation failed');
    return shader;
  }

  class BorderLayer{
    constructor(id='workbench-extrusion-borders'){this.id=id;this.type='custom';this.renderingMode='3d';this.mesh=null;this.dirty=true;this.visible=false}
    setMesh(mesh){this.mesh=mesh;this.visible=Boolean(mesh?.indices?.length);this.dirty=true;this.map?.triggerRepaint()}
    onAdd(map,gl){
      this.map=map;
      const vertex=compile(gl,gl.VERTEX_SHADER,'#version 300 es\nuniform mat4 u_matrix;in vec3 a_position;in vec4 a_color;out vec4 v_color;void main(){gl_Position=u_matrix*vec4(a_position,1.0);v_color=a_color;}');
      const fragment=compile(gl,gl.FRAGMENT_SHADER,'#version 300 es\nprecision mediump float;in vec4 v_color;out vec4 frag_color;void main(){frag_color=v_color;}');
      this.program=gl.createProgram();gl.attachShader(this.program,vertex);gl.attachShader(this.program,fragment);gl.linkProgram(this.program);
      if(!gl.getProgramParameter(this.program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(this.program)||'Extrusion border shader linking failed');
      this.position=gl.getAttribLocation(this.program,'a_position');this.color=gl.getAttribLocation(this.program,'a_color');this.matrix=gl.getUniformLocation(this.program,'u_matrix');this.vertexBuffer=gl.createBuffer();this.indexBuffer=gl.createBuffer();
    }
    upload(gl){gl.bindBuffer(gl.ARRAY_BUFFER,this.vertexBuffer);gl.bufferData(gl.ARRAY_BUFFER,this.mesh?.vertices||new Float32Array(),gl.DYNAMIC_DRAW);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,this.indexBuffer);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,this.mesh?.indices||new Uint32Array(),gl.DYNAMIC_DRAW);this.count=this.mesh?.indices?.length||0;this.dirty=false}
    render(gl,parameters){
      if(!this.visible||!this.mesh)return;if(this.dirty)this.upload(gl);
      const matrix=parameters?.defaultProjectionData?.mainMatrix||parameters?.modelViewProjectionMatrix||parameters;
      gl.useProgram(this.program);gl.uniformMatrix4fv(this.matrix,false,matrix);gl.enable(gl.DEPTH_TEST);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
      gl.bindBuffer(gl.ARRAY_BUFFER,this.vertexBuffer);gl.enableVertexAttribArray(this.position);gl.vertexAttribPointer(this.position,3,gl.FLOAT,false,28,0);gl.enableVertexAttribArray(this.color);gl.vertexAttribPointer(this.color,4,gl.FLOAT,false,28,12);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,this.indexBuffer);gl.drawElements(gl.LINES,this.count,gl.UNSIGNED_INT,0);this.renderCount=(this.renderCount||0)+1;
    }
    onRemove(_map,gl){gl.deleteBuffer(this.vertexBuffer);gl.deleteBuffer(this.indexBuffer);gl.deleteProgram(this.program)}
  }

  const api={polygons,buildMesh,BorderLayer};global.WorkbenchExtrusionBorders=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
