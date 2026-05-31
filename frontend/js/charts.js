function createAffinityChart(selector, data, options = {}) {
  const container = d3.select(selector);
  container.html('');

  if (!data || !data.length) {
    container.append('div')
      .attr('class', 'empty-state')
      .html('<p>No artists synced yet.</p><p>Click "Sync Library" to load your top artists.</p>');
    return;
  }

  const BAR_W = options.barWidth  || 90;
  const BAR_H = options.barHeight || 6;
  const maxScore = d3.max(data, d => d.affinity_score) || 100;

  const rows = container.selectAll('div.artist-row')
    .data(data)
    .join('div')
    .attr('class', 'artist-row');

  rows.append('img')
    .attr('class', 'artist-row-img')
    .attr('src', d => d.artist_image_url || '')
    .attr('alt', d => d.artist_name)
    .on('error', function () { d3.select(this).style('display', 'none'); });

  const info = rows.append('div').attr('class', 'artist-row-info');

  info.append('div')
    .attr('class', 'artist-row-name')
    .text(d => d.artist_name);

  // SVG bar sits below the name inside the info column
  const svg = info.append('svg')
    .attr('width', BAR_W)
    .attr('height', BAR_H)
    .style('display', 'block')
    .style('margin-top', '5px');

  svg.append('rect')
    .attr('width', BAR_W)
    .attr('height', BAR_H)
    .attr('rx', BAR_H / 2)
    .attr('fill', 'var(--border)');

  svg.append('rect')
    .attr('width', 0)
    .attr('height', BAR_H)
    .attr('rx', BAR_H / 2)
    .attr('fill', 'var(--accent)')
    .transition()
    .duration(500)
    .ease(d3.easeCubicOut)
    .attr('width', d => (d.affinity_score / maxScore) * BAR_W);

  // Score number on the right edge of the row
  rows.append('div')
    .attr('class', 'artist-row-score')
    .style('min-width', '26px')
    .style('text-align', 'right')
    .style('flex-shrink', '0')
    .text(d => Math.round(d.affinity_score));
}
