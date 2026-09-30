/**
 * Charting Engine
 * ===============
 * Handles candlestick charts, volume histograms, and technical overlays.
 */

class TradingChart {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.chart = null;
        this.candleSeries = null;
        this.volumeSeries = null;
        this.ema9Series = null;
        this.ema21Series = null;
        this.showEma = true;
        this.showVolume = true;

        this.init();
    }

    init() {
        if (!this.container || typeof LightweightCharts === 'undefined') {
            console.warn("LightweightCharts library not loaded or container not found");
            return;
        }

        // Chart options for dark theme
        const chartOptions = {
            layout: {
                background: { color: '#182030' },
                textColor: '#94a3b8',
                fontFamily: 'JetBrains Mono, Inter, sans-serif',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.04)' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: {
                    color: 'rgba(0, 209, 143, 0.4)',
                    width: 1,
                    style: LightweightCharts.LineStyle.Dashed,
                },
                horzLine: {
                    color: 'rgba(0, 209, 143, 0.4)',
                    width: 1,
                    style: LightweightCharts.LineStyle.Dashed,
                },
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.08)',
                autoScale: true,
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.08)',
                timeVisible: true,
                secondsVisible: false,
            },
            handleScroll: { mouseWheel: true, pressedMouseMove: true },
            handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
        };

        this.chart = LightweightCharts.createChart(this.container, chartOptions);

        // Candlestick Series (supports v4 and v5)
        const candleOpts = {
            upColor: '#00d18f',
            downColor: '#ff4757',
            borderVisible: false,
            wickUpColor: '#00d18f',
            wickDownColor: '#ff4757',
        };
        if (typeof this.chart.addCandlestickSeries === 'function') {
            this.candleSeries = this.chart.addCandlestickSeries(candleOpts);
        } else if (LightweightCharts.CandlestickSeries) {
            this.candleSeries = this.chart.addSeries(LightweightCharts.CandlestickSeries, candleOpts);
        }

        // Volume Series (Overlay at bottom)
        const volOpts = {
            color: '#38bdf8',
            priceFormat: { type: 'volume' },
            priceScaleId: '', // overlay
            scaleMargins: {
                top: 0.8,
                bottom: 0,
            },
        };
        if (typeof this.chart.addHistogramSeries === 'function') {
            this.volumeSeries = this.chart.addHistogramSeries(volOpts);
        } else if (LightweightCharts.HistogramSeries) {
            this.volumeSeries = this.chart.addSeries(LightweightCharts.HistogramSeries, volOpts);
        }

        // EMA 9 Line
        const ema9Opts = {
            color: '#38bdf8',
            lineWidth: 2,
            title: 'EMA 9',
            priceScaleId: 'right',
        };
        if (typeof this.chart.addLineSeries === 'function') {
            this.ema9Series = this.chart.addLineSeries(ema9Opts);
        } else if (LightweightCharts.LineSeries) {
            this.ema9Series = this.chart.addSeries(LightweightCharts.LineSeries, ema9Opts);
        }

        // EMA 21 Line
        const ema21Opts = {
            color: '#f59e0b',
            lineWidth: 2,
            title: 'EMA 21',
            priceScaleId: 'right',
        };
        if (typeof this.chart.addLineSeries === 'function') {
            this.ema21Series = this.chart.addLineSeries(ema21Opts);
        } else if (LightweightCharts.LineSeries) {
            this.ema21Series = this.chart.addSeries(LightweightCharts.LineSeries, ema21Opts);
        }

        // Handle window resizing
        window.addEventListener('resize', () => {
            if (this.chart && this.container) {
                this.chart.applyOptions({
                    width: this.container.clientWidth,
                    height: this.container.clientHeight,
                });
            }
        });

        // Initial resize
        setTimeout(() => {
            if (this.chart && this.container) {
                this.chart.applyOptions({
                    width: this.container.clientWidth,
                    height: 380,
                });
            }
        }, 100);
    }

    setCandleData(candles) {
        if (!this.candleSeries || !candles || !candles.length) return;

        const formattedCandles = candles.map(c => {
            const timeVal = Math.floor(new Date(c.time).getTime() / 1000);
            return {
                time: timeVal,
                open: c.open,
                high: c.high,
                low: c.low,
                close: c.close,
            };
        });

        const formattedVolumes = candles.map(c => {
            const timeVal = Math.floor(new Date(c.time).getTime() / 1000);
            return {
                time: timeVal,
                value: c.volume,
                color: c.close >= c.open ? 'rgba(0, 209, 143, 0.3)' : 'rgba(255, 71, 87, 0.3)',
            };
        });

        // Set series data
        this.candleSeries.setData(formattedCandles);
        if (this.showVolume) {
            this.volumeSeries.setData(formattedVolumes);
        }

        // Calculate and set EMAs
        if (this.showEma) {
            const ema9 = this.calculateEMA(formattedCandles, 9);
            const ema21 = this.calculateEMA(formattedCandles, 21);
            this.ema9Series.setData(ema9);
            this.ema21Series.setData(ema21);
        }

        this.chart.timeScale().fitContent();
    }

    updateTick(candle) {
        if (!this.candleSeries || !candle) return;
        const timeVal = Math.floor(new Date(candle.time).getTime() / 1000);

        this.candleSeries.update({
            time: timeVal,
            open: candle.open,
            high: candle.high,
            low: candle.low,
            close: candle.close,
        });

        if (this.showVolume) {
            this.volumeSeries.update({
                time: timeVal,
                value: candle.volume,
                color: candle.close >= candle.open ? 'rgba(0, 209, 143, 0.3)' : 'rgba(255, 71, 87, 0.3)',
            });
        }
    }

    calculateEMA(candles, period) {
        const result = [];
        const k = 2 / (period + 1);
        let ema = 0;

        for (let i = 0; i < candles.length; i++) {
            const close = candles[i].close;
            if (i === 0) {
                ema = close;
            } else {
                ema = close * k + ema * (1 - k);
            }

            if (i >= period - 1) {
                result.push({
                    time: candles[i].time,
                    value: parseFloat(ema.toFixed(2)),
                });
            }
        }
        return result;
    }

    toggleEMA(visible) {
        this.showEma = visible;
        this.ema9Series.applyOptions({ visible });
        this.ema21Series.applyOptions({ visible });
    }

    toggleVolume(visible) {
        this.showVolume = visible;
        this.volumeSeries.applyOptions({ visible });
    }
}
