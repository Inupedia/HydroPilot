import {
  Cartesian2,
  Cartesian3,
  Color,
  DistanceDisplayCondition,
  GeographicTilingScheme,
  HeightReference,
  HorizontalOrigin,
  LabelStyle,
  Math as CesiumMath,
  NearFarScalar,
  PolylineGlowMaterialProperty,
  UrlTemplateImageryProvider,
  VerticalOrigin,
  Viewer,
  buildModuleUrl,
} from 'cesium'
import type { HydroObject, HydroState } from '../types'
import { flowSceneVisual, stateValueAt, storageSceneVisual, type FlowSeverity } from './forecastScene'

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

function elevatedLinePositions(object: HydroObject, heightM: number): Cartesian3[] | null {
  if (object.geometry.type !== 'LineString') return null
  const coordinates = object.geometry.coordinates as number[][]
  if (!Array.isArray(coordinates) || coordinates.length < 2) return null
  return coordinates.map((coordinate) => Cartesian3.fromDegrees(Number(coordinate[0]), Number(coordinate[1]), heightM))
}

function flowColor(severity: FlowSeverity): Color {
  if (severity === 'extreme') return Color.fromCssColorString('#ff5d5d')
  if (severity === 'high') return Color.fromCssColorString('#ffb84d')
  if (severity === 'elevated') return Color.fromCssColorString('#42ddff')
  return COLORS.river
}

function finiteProperty(value: unknown): number | null {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
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
  if (viewer.scene.skyAtmosphere) viewer.scene.skyAtmosphere.show = true
  if (viewer.scene.sun) viewer.scene.sun.show = false
  if (viewer.scene.moon) viewer.scene.moon.show = false

  viewer.camera.setView({
    destination: Cartesian3.fromDegrees(-121.25, 39.35, 470_000),
    orientation: {
      heading: CesiumMath.toRadians(345),
      pitch: CesiumMath.toRadians(-58),
      roll: 0,
    },
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
      const flow = stateValueAt(states, object.id, 'flow', timestamp)
      const visual = flowSceneVisual(flow)
      const color = flowColor(visual.severity)
      const highlighted = highlightedIds.has(object.id)
      const elevatedPositions = flow == null ? null : elevatedLinePositions(object, visual.wallHeightM)
      const minimumHeights = elevatedPositions?.map(() => 40)

      viewer.entities.add({
        id: object.id,
        name: object.name,
        description: flow != null
          ? `<b>${object.name}</b><br/>3D preview flow: ${flow.toFixed(1)} m³/s<br/>T+${timestamp} min<br/>Severity: ${visual.severity}`
          : `<b>${object.name}</b><br/>Directed water-network reach`,
        polyline: {
          positions: Cartesian3.fromDegreesArray(coordinates),
          width: highlighted ? Math.max(visual.width, 7) : visual.width,
          material: highlighted ? COLORS.riverHighlighted : color,
          clampToGround: true,
          depthFailMaterial: highlighted ? COLORS.riverHighlighted : color.withAlpha(0.55),
        },
        wall: elevatedPositions ? {
          positions: elevatedPositions,
          minimumHeights,
          material: color.withAlpha(visual.severity === 'normal' ? 0.12 : 0.22),
          outline: visual.severity === 'high' || visual.severity === 'extreme',
          outlineColor: color.withAlpha(0.8),
        } : undefined,
      })

      if (elevatedPositions) {
        viewer.entities.add({
          id: `${object.id}-forecast-ribbon`,
          name: `${object.name} forecast flow ribbon`,
          polyline: {
            positions: elevatedPositions,
            width: visual.width + 2,
            material: new PolylineGlowMaterialProperty({
              glowPower: visual.glow,
              taperPower: 0.65,
              color: color.withAlpha(0.95),
            }),
          },
        })
      }
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
    const storage = object.object_type === 'reservoir' ? stateValueAt(states, object.id, 'storage', timestamp) : null
    const inflow = object.object_type === 'reservoir' ? stateValueAt(states, object.id, 'inflow', timestamp) : null
    const release = object.object_type === 'reservoir' ? stateValueAt(states, object.id, 'release', timestamp) : null
    const maxStorage = object.object_type === 'reservoir' ? finiteProperty(object.properties.max_storage_m3) : null
    const storageVisual = storageSceneVisual(storage, maxStorage)
    const reservoirDescription = storage != null
      ? `<b>${object.name}</b><br/>T+${timestamp} min<br/>Storage: ${(storage / 1e9).toFixed(3)} B m³${maxStorage ? `<br/>Capacity: ${(storageVisual.ratio * 100).toFixed(1)}%` : ''}${inflow != null ? `<br/>Inflow: ${inflow.toFixed(0)} m³/s` : ''}${release != null ? `<br/>Release: ${release.toFixed(0)} m³/s` : ''}`
      : `<b>${object.name}</b><br/>Type: ${object.object_type}<br/>Source: public demo fixture`

    viewer.entities.add({
      id: object.id,
      name: object.name,
      description: object.object_type === 'reservoir'
        ? reservoirDescription
        : `<b>${object.name}</b><br/>Type: ${object.object_type}<br/>Source: public demo fixture`,
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
        semiMajorAxis: 14_000 * storageVisual.radiusScale,
        semiMinorAxis: 8_000 * storageVisual.radiusScale,
        material: COLORS.reservoir.withAlpha(storage == null ? 0.34 : 0.24 + storageVisual.ratio * 0.2),
        outline: true,
        outlineColor: COLORS.reservoir.withAlpha(0.9),
        height: 0,
      } : undefined,
    })

    if (object.object_type === 'reservoir' && storage != null) {
      viewer.entities.add({
        id: `${object.id}-forecast-volume`,
        name: `${object.name} forecast storage volume`,
        description: reservoirDescription,
        position: Cartesian3.fromDegrees(longitude, latitude, storageVisual.columnHeightM / 2),
        cylinder: {
          length: storageVisual.columnHeightM,
          topRadius: 5_500 * storageVisual.radiusScale,
          bottomRadius: 7_500 * storageVisual.radiusScale,
          material: COLORS.reservoir.withAlpha(0.24),
          outline: true,
          outlineColor: COLORS.reservoir.withAlpha(0.72),
          numberOfVerticalLines: 12,
        },
      })
    }
  }
}
