window.addEventListener('load', async () => {
  await window.isaacReplay.ready;
  window.isaacReplay.setExperience({schemaVersion:'v1.0', chapters:[
    {id:'overview',clipIndex:0,startSeconds:0,title:'Overview',caption:'Two parts enter the cell.',camera:{position:[7,6,9],target:[0,0,0]},transitionSeconds:0},
    {id:'inspect',clipIndex:0,startSeconds:9,title:'Inspect',caption:'Part A reaches inspection.',objectId:'/World/Products/PartA',label:'Part A',camera:{position:[2,4,5],target:[-1,0,0]},transitionSeconds:1},
    {id:'place',clipIndex:0,startSeconds:21,title:'Place',caption:'Part A moves to the output bin.',objectId:'/World/Products/PartA',label:'Delivered part',camera:{position:[5,4,5],target:[2,0,0]},transitionSeconds:1}
  ]});
  window.isaacReplay.seek(0);
});
