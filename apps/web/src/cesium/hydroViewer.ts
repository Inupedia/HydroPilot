import {
  Cartesian2,
  Cartesian3,
  Color,
  DistanceDisplayCondition,
  GeographicTilingScheme,
  HeightReference,
  HorizontalOrigin,
  LabelStyle,
  NearFarScalar,
  Rectangle,
  UrlTemplateImageryProvider,
  VerticalOrigin,
  Viewer,
  buildModuleUrl,
} from 'cesium'
import type { HydroObject, HydroState } from '../types'

const COLORS = {
  river: Color.fromCssColorString('#36c9f5'),
  riverHighlighted: Color.fromCssColorString('#ffd166'),
  reservoir: Color.fromCssColorString('#16a9e0'),
  dam: Color.fromCssColorString('#ffc857'),
  gauge: Color.fromCssColorString('#4ef0b7'),
  control: Color.fromCssColorString('#ff6b6b'),
  label: Color.fromCssColorString('#eafaff'),
  labelBackground: Color.fromCssColorString('#061522').withAlpha(0.82),
}

function pointCoordinates(object: HydroObject): [number, number] | null {
  if (object.geometry.type !== 'Point') return null
  const coordinates = object.geometry.coordinates as number[]
  if (!Array.isArray(coordinates) || coordinates.length < 2) return null
  return [Number(coordinates[0]), Number(coordinates[1])]
}

function lineCoordinates(object: HydroObject): number[] | null {
  if (object.geometry.type !== 'LineString') return null
  const coordinates = object.geometry.coordinates as number[][]
  if (!Array.isArray(coordinates) || coordinates.length < 2) return null
  return coordinates.flatMap((coordinate) => [Number(coordinate[0]), Number(coordinate[1])])
}

function currentState(states: HydroState[], objectId: string, timestamp: number): HydroState | undefined {
  return states.find((state) => state.object_id === objectId && state.timestamp_minutes === timestamp)
}

function flowVisual(state: HydroState | undefined): { width: number; color: Color } {
  if (!state || state.variable !== 'flow') return { width: 3.5, color: COLORS.river }
  const flow = Math.max(0, state.value)
  if (flow >= 2500) return { width: 8, color: Color.fromCssColorString('#ff5d5d') }
  if (flow >= 1600) return { width: 6.5, color: Color.fromCssColorString('#ffb84d') }
  if (flow >= 800) return { width: 5, color: Color.fromCssColorString('#42ddff') }
  return { width: 4, color: COLORS.river }
}

export function createHydroViewer(container: HTMLElement): Viewer {
  const viewer = new Viewer(container, {
    animation: false,
    timeline: false,
    baseLayerPicker: false,
    baseLayer: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    fullscreenButton: false,
    infoBox: true,
    selectionIndicator: true,
    shouldAnimate: true,
  })

  const naturalEarth = new UrlTemplateImageryProvider({
    url: `${buildModuleUrl('Assets/Textures/NaturalEarthII')}/{z}/{x}/{reverseY}.jpg`,
    tilingScheme: new GeographicTilingScheme(),
    maximumLevel: 5,
  })
  viewer.imageryLayers.addImageryProvider(naturalEarth)

  viewer.scene.backgroundColor = Color.fromCssColorString('#020b12')
  viewer.scene.globe.baseColor = Color.fromCssColorString('#0b2737')
  viewer.scene.globe.enableLighting = false
  viewer.scene.fog.enabled = false
  viewer.scene.skyAtmosphere.show = true
  viewer.scene.sun.show = false
  viewer.scene.moon.show = false

  viewer.camera.setView({
    destination: Rectangle.fromDegrees(-123.1, 37.5, -119.7, 41.25),
  })

  return viewer
}

export function renderHydroScene(
  viewer: Viewer,
  objects: HydroObject[],
  highlightedIds: Set<string>,
  states: HydroState[],
  timestamp: number,
): void {
  viewer.entities.removeAll()

  for (const object of objects) {
    if (object.object_type === 'river_reach') {
      const coordinates = lineCoordinates(object)
      if (!coordinates) continue
      const state = currentState(states, object.id, timestamp)
      const visual = flowVisual(state)
      const highlighted = highlightedIds.has(object.id)
      viewer.entities.add({
        id: object.id,
        name: object.name,
        description: state
          ? `<b>${object.name}</b><br/>Flow: ${state.value.toFixed(1)} ${state.unit}<br/>t = ${timestamp} min`
          : `<b>${object.name}</b><br/>Directed water-network reach`,
        polyline: {
          positions: Cartesian3.fromDegreesArray(coordinates),
          width: highlighted ? Math.max(visual.width, 7) : visual.width,
          material: highlighted ? COLORS.riverHighlighted : visual.color,
          clampToGround: true,
          depthFailMaterial: highlighted ? COLORS.riverHighlighted : visual.color.withAlpha(0.55),
        },
      })
      continue
    }

    const coordinates = pointCoordinates(object)
    if (!coordinates) continue
    const [longitude, latitude] = coordinates
    const highlighted = highlightedIds.has(object.id)
    const color = object.object_type === 'dam'
      ? COLORS.dam
      : object.object_type === 'gauge'
        ? COLORS.gauge
        : object.object_type === 'control_point'
          ? COLORS.control
          : COLORS.reservoir
    const size = object.object_type === 'reservoir' ? 16 : highlighted ? 17 : 13

    viewer.entities.add({
      id: object.id,
      name: object.name,
      description: `<b>${object.name}</b><br/>Type: ${object.object_type}<br/>Source: public demo fixture`,
      position: Cartesian3.fromDegrees(longitude, latitude, object.object_type === 'dam' ? 550 : 350),
      point: {
        pixelSize: size,
        color,
        outlineColor: highlighted ? Color.WHITE : Color.fromCssColorString('#052238'),
        outlineWidth: highlighted ? 3 : 2,
        heightReference: HeightReference.NONE,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scaleByDistance: new NearFarScalar(2.5e5, 1.25, 2.5e6, 0.75),
      },
      label: {
        text: object.name.replace(' Demo Object', '').replace(' Demo', ''),
        font: '600 13px sans-serif',
        fillColor: COLORS.label,
        outlineColor: Color.BLACK,
        outlineWidth: 2,
        style: LabelStyle.FILL_AND_OUTLINE,
        showBackground: true,
        backgroundColor: COLORS.labelBackground,
        backgroundPadding: new Cartesian2(8, 5),
        horizontalOrigin: HorizontalOrigin.LEFT,
        verticalOrigin: VerticalOrigin.CENTER,
        pixelOffset: new Cartesian2(14, 0),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        distanceDisplayCondition: new DistanceDisplayCondition(0, 2_400_000),
      },
      ellipse: object.object_type === 'reservoir' ? {
        semiMajorAxis: 14_000,
        semiMinorAxis: 8_000,
        material: COLORS.reservoir.withAlpha(0.34),
        outline: true,
        outlineColor: COLORS.reservoir.withAlpha(0.9),
        height: 0,
      } : undefined,
    })
  }
}
